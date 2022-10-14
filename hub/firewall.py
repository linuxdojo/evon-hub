from itertools import chain

import os
os.environ["XTABLES_LIBDIR"] = "/usr/lib64/xtables"
import iptc

import hub.models


def apply_rule(rule):
    """
    Takes a hub.models.Rule instance and creates an iptables chain with rules reflecting the object properties
    """

    # collect properties
    destination_protocol = rule.destination_protocol.lower()
    destination_ports = [p.replace("-", ":") for p in rule.destination_ports.split(",") if p]
    chain_name = f"evon-rule-{rule.pk}"
    source_objects = list(
        set(
            chain(
                rule.source_users.all(),
                hub.models.User.objects.filter(groups__in=rule.source_groups.all())
            )
        )
    ) + list(
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
    for source in source_ipv4_addresses:
        rule = iptc.Rule()
        if destination_protocol != "all":
            rule.protocol = destination_protocol
        rule.src = source
        for portspec in destination_ports:
            match = rule.create_match(destination_protocol)
            match.dport = portspec
        rule.target = iptc.Target(rule, "ACCEPT")
        iptc_chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), chain_name)
        iptc_chain.insert_rule(rule)


def delete_rule(rule):
    """
    Takes a hub.models.Rule instance and deletes the corresponding iptables chain
    """
    chain_name = f"evon-rule-{rule.pk}"
    if chain_name in iptc.easy.get_chains('filter'):
        iptc.easy.flush_chain("filter", chain_name)
        iptc.easy.delete_chain("filter", chain_name)

