from itertools import chain
import uuid

import iptc

from eapi.settings import EVON_HUB_CONFIG
from eapi.settings import EVON_VARS
from evon.log import get_evon_logger
import hub.models


logger = get_evon_logger()


def apply_rule(rule):
    """
    Takes a hub.models.Rule instance and creates an iptables chain with rules reflecting the object properties
    """

    # collect properties
    destination_protocol = rule.destination_protocol.lower()
    destination_ports = [p.replace("-", ":") for p in rule.destination_ports.split(",") if p]
    chain_name = rule.get_chain_name()
    source_objects = \
        list(
            set(
                chain(
                    rule.source_users.all(),
                    hub.models.User.objects.filter(groups__in=rule.source_groups.all())
                )
            )
        ) + \
        list(
            set(
                chain(
                    rule.source_servers.all(),
                    hub.models.Server.objects.filter(server_groups__in=rule.source_servergroups.all())
                )
            )
        )
    source_ipv4_addresses = [s.ipv4_address if isinstance(s, hub.models.Server) else s.userprofile.ipv4_address for s in source_objects]

    # Create iptables chain
    if chain_name in iptc.easy.get_chains('filter'):
        iptc.easy.flush_chain("filter", chain_name)
    else:
        iptc.easy.add_chain("filter", chain_name)

    # create rules and apply them to chain
    for source_ipv4_address in source_ipv4_addresses:
        rule = iptc.Rule()
        if destination_protocol != "all":
            rule.protocol = destination_protocol
        rule.src = source_ipv4_address
        for portspec in destination_ports:
            match = rule.create_match(destination_protocol)
            match.dport = portspec
        rule.target = iptc.Target(rule, "ACCEPT")
        iptc_chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), chain_name)
        iptc_chain.insert_rule(rule)


def apply_policy(policy):
    """
    Takes a hub.models.Policy instance and creates iptables rules in the evon-policy chain reflecting the object properties
    """
    target_objects = \
        list(
            set(
                chain(
                    policy.servers.all(),
                    hub.models.Server.objects.filter(server_groups__in=policy.servergroups.all())
                )
            )
        )
    target_chains = [r.get_chain_name() for r in policy.rules.all()]
    policy_rule_comment = f"evon-policy-{policy.pk}"
    ipt_chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), "evon-policy")
    # delete policy rules here before recreating below.
    delete_policy(policy)

    ##### iptc bugfix workaround 
    # bug: where first rule in interation sometimes not being inserted, happens
    # when rules are manually deleted using iptables command then re-added.
    # we insert a temp ICMP rule with a uuid in the comment, then if it exists, we delete it.
    # subsequent insertions will work.
    tmp_chain_handle = iptc.Chain(iptc.Table(iptc.Table.FILTER), "evon-policy")
    dummy_rule = iptc.Rule()
    dummy_comment = str(uuid.uuid4())
    dummy_rule.protocol = "icmp"
    match = iptc.Match(dummy_rule, "comment")
    match.comment = dummy_comment
    dummy_rule.add_match(match)
    dummy_rule.target = iptc.Target(dummy_rule, "ACCEPT")
    tmp_chain_handle.insert_rule(dummy_rule)
    tmp_chain_handle = iptc.Chain(iptc.Table(iptc.Table.FILTER), "evon-policy")
    tmp_rule_list = [r for r in tmp_chain_handle.rules if dummy_comment in [m.comment for m in r.matches]]
    if tmp_rule_list:
        tmp_rule = tmp_rule_list.pop()
        tmp_chain_handle.delete_rule(tmp_rule)
    ##### end iptc bugfix workaround

    for target_chain in target_chains:
        for target_address in [t.ipv4_address for t in target_objects]:
            rule = iptc.Rule()
            rule.dst = target_address
            match = iptc.Match(rule, "comment")
            match.comment = policy_rule_comment
            rule.add_match(match)
            rule.target = iptc.Target(rule, target_chain)
            ipt_chain.insert_rule(rule)


def delete_iptrules_by_target_name(chain_name, target_name):
    """
    deletes an iptables rule in chain `chain_name` with target `taget_name`
    """
    chain_handle = iptc.Chain(iptc.Table(iptc.Table.FILTER), chain_name)
    rule_list = True
    while rule_list:
        rule_list = [r for r in chain_handle.rules if r.target.name == target_name]
        # XXX we can only delete one rule at a time, then need to regenerate rule_list. Consider toggling autocommit in iptc.
        if rule_list:
            chain_handle.delete_rule(rule_list.pop())


def delete_iptrules_by_comment(chain_name, comment):
    """
    deletes all rules matching `comment` in iptables chain with name `chain_name`
    """
    chain_handle = iptc.Chain(iptc.Table(iptc.Table.FILTER), chain_name)
    rule_list = True
    while rule_list:
        rule_list = [r for r in chain_handle.rules if comment in [m.comment for m in r.matches]]
        # XXX we can only delete one rule at a time, then need to regenerate rule_list. Consider toggling autocommit in iptc.
        if rule_list:
            chain_handle.delete_rule(rule_list.pop())

    
def delete_chain(chain_name):
    """
    Deletes an iptables chain matching `chain_name`
    """
    if chain_name in iptc.easy.get_chains('filter'):
        iptc.easy.flush_chain("filter", chain_name)
        # delete chain refs in "evon-policy" chain
        for cn in iptc.easy.get_chains('filter'):
            delete_iptrules_by_target_name(cn, chain_name)
        iptc.easy.delete_chain("filter", chain_name)


def delete_rule(rule):
    """
    Takes a hub.models.Rule instance and deletes the corresponding iptables chain
    """
    delete_chain(rule.get_chain_name())


def delete_policy(policy):
    """
    Takes a hub.models.Policy and deletes the corresponding iptables rules in the evon-policy chain
    """
    chain_name = "evon-policy"
    policy_comment = f"evon-policy-{policy.pk}"
    delete_iptrules_by_comment(chain_name, policy_comment)


def sync_all_rules():
    """
    Removes any orphaned Rule chains and creates Rule chains in iptables from the set of all Hub Rules
    """
    # remove orpans
    all_iptables_rule_chains = [c for c in iptc.easy.get_chains('filter') if c.startswith(hub.models.Rule.chain_name_prefix)]
    all_rule_chain_names = [r.get_chain_name() for r in hub.models.Rule.objects.all()]
    for chain_name in all_iptables_rule_chains:
        if not chain_name in all_rule_chain_names:
            delete_chain(chain_name)
    # create chains
    for rule in hub.models.Rule.objects.all():
        apply_rule(rule)


def sync_all_policies():
    """
    Syncs all policy rules in the evon-policy chain, removing any orphans
    """
    iptc.easy.flush_chain("filter", "evon-policy")
    for policy in hub.models.Policy.objects.all():
        apply_policy(policy)
    

def delete_all(flush_only=True):
    """
    Delete all rules and policies and revert to initialised state.
    If flush_only=False, delete absolutely all evon-related firewall rules and chains.
    """
    # flush policy chain
    if "evon-policy" in iptc.easy.get_chains('filter'):
        iptc.easy.flush_chain("filter", "evon-policy")
    # delete rule chains
    for chain_name in [c for c in iptc.easy.get_chains('filter') if c.startswith(hub.models.Rule.chain_name_prefix)]:
        delete_chain(chain_name)
    if not flush_only:
        # delete evon-main ref in FORWARD chain
        table = iptc.Table(iptc.Table.FILTER)
        ipt_chain = iptc.Chain(table, "FORWARD")
        for rule in ipt_chain.rules:
            if rule.target.name == "evon-main":
                ipt_chain.delete_rule(rule)
                break
        # flush and delete evon-main chain
        delete_chain("evon-main")
        # flush and delete evon-policy chain
        delete_chain("evon-policy")


def kill_orphan_servers():
    """
    sends the kill command to the server openvpn management interface for any connected servers that do not have an entry in the Servers table
    """
    vpn = EVON_HUB_CONFIG["vpn_mgmt_servers"]
    vpn.connect()
    connected_uuids = {v.common_name for _, v in vpn.get_status().routing_table.items()}
    vpn.disconnect()
    existing_uuids = {s.uuid for s in hub.models.Server.objects.all()}
    orphan_uuids = connected_uuids.difference(existing_uuids)
    vpn.connect()
    for uuid in orphan_uuids:
        logger.info(f"killing orphan connection with UUID: {uuid}")
        result = vpn.send_command(f"kill {uuid}")
        logger.info(f"killed orphan connection for UUID {uuid} with result: {result}")
    vpn.disconnect()


def kill_inactive_users(extra_user=None):
    """
    sends the kill command to the user openvpn management interface for any users that are set to not active
    if `extra_user` is specified, also kill the connection whose common name == `extra_user` if connected.
    """
    vpn = EVON_HUB_CONFIG["vpn_mgmt_users"]
    vpn.connect()
    connected_usernames = {v.common_name for _, v in vpn.get_status().routing_table.items()}
    vpn.disconnect()
    existing_inactive_usernames = {u.username for u in hub.models.User.objects.all() if not u.is_active}
    if extra_user:
        existing_inactive_usernames.add(extra_user)
    usernames_to_kill = connected_usernames.intersection(existing_inactive_usernames)
    vpn.connect()
    for username in usernames_to_kill:
        logger.info(f"killing connection for deactivated user: {username}")
        result = vpn.send_command(f"kill {username}")
        logger.info(f"killed connection for deactivated user {username} with result: {result}")
    vpn.disconnect()


def init(full=True):
    """
    Initialise iptables chains for evon Rules and Policies.
    if `full` == False, just create the core chains.
    """
    # create core chains
    core_chains = ["evon-main", "evon-policy"]
    for chain_name in core_chains:
        if chain_name not in iptc.easy.get_chains('filter'):
            iptc.easy.add_chain("filter", chain_name)
    # add rule to chain FORWARD -> evon-main
    main_chain_comment = "evon-forward-to-evon-main"
    subnet_key = EVON_VARS["subnet_key"]
    if not [r for r in iptc.easy.dump_table('filter')['FORWARD'] if r.get("comment", {}).get("comment") == main_chain_comment]:
        rule = iptc.Rule()
        match = iptc.Match(rule, "iprange")
        match.src_range = f"100.{ subnet_key }.208.1-100.{ subnet_key }.255.254"
        rule.add_match(match)
        match = iptc.Match(rule, "comment")
        match.comment = main_chain_comment
        rule.add_match(match)
        rule.target = iptc.Target(rule, "evon-main")
        ipt_chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), "FORWARD")
        ipt_chain.insert_rule(rule)
    # add main rules
    iptc.easy.flush_chain("filter", "evon-main")
    # insert catch all evon traffic to drop
    ipt_chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), "evon-main")
    rule = iptc.Rule()
    match = iptc.Match(rule, "iprange")
    match.src_range = f"100.{ subnet_key }.208.1-100.{ subnet_key }.255.254"
    rule.add_match(match)
    rule.target = iptc.Target(rule, "DROP")
    ipt_chain.insert_rule(rule)
    # insert all->evon-policy
    rule = iptc.Rule()
    rule.target = iptc.Target(rule, "evon-policy")
    ipt_chain.insert_rule(rule)
    # insert established/related -> accept
    rule = iptc.Rule()
    match = iptc.Match(rule, "state")
    match.state = "RELATED,ESTABLISHED"
    rule.add_match(match)
    rule.target = iptc.Target(rule, "ACCEPT")
    ipt_chain.insert_rule(rule)
    # insert icmp conntrack established/related -> accept
    rule = iptc.Rule()
    rule.protocol = "icmp"
    match = iptc.Match(rule, "conntrack")
    match.ctstate = "RELATED,ESTABLISHED"
    rule.add_match(match)
    rule.target = iptc.Target(rule, "ACCEPT")
    ipt_chain.insert_rule(rule)
    # insert udp conntrack established/related -> accept
    rule = iptc.Rule()
    rule.protocol = "udp"
    match = iptc.Match(rule, "conntrack")
    match.ctstate = "RELATED,ESTABLISHED"
    rule.add_match(match)
    rule.target = iptc.Target(rule, "ACCEPT")
    ipt_chain.insert_rule(rule)
    # insert tcp conntrack established/related -> accept
    rule = iptc.Rule()
    rule.protocol = "tcp"
    match = iptc.Match(rule, "conntrack")
    match.ctstate = "RELATED,ESTABLISHED"
    rule.add_match(match)
    rule.target = iptc.Target(rule, "ACCEPT")
    ipt_chain.insert_rule(rule)
    # sync all rules and policies
    if full:
        sync_all_rules()
        sync_all_policies()
