# Evon Bootstrap for Windows

### register params
param(
    [Parameter (Mandatory = $false)] [String]$Apikey,
    [Parameter (Mandatory = $false)] [String]$Hostname,
    [Parameter (Mandatory = $false)] [String]$Uuid,
    [Parameter (Mandatory = $false)] [String]$Extraconf,
    [Parameter (Mandatory = $false)] [Switch]$Uninstall,
    [Parameter (Mandatory = $false)] [Switch]$Version,
    [Parameter (Mandatory = $false)] [Switch]$Help
)

### define vars
$ver = "{{ evon_version }}"
$account_domain = "{{ account_domain }}"
$subnet_key = "{{ subnet_key }}"
$evon_hub_peer = "100.$subnet_key.224.1"
$pf_dir = ([System.Environment]::GetEnvironmentVariable('ProgramFiles'))
$ovpn_conf_dir = "$pf_dir\OpenVPN\config-auto"
$extra_config_default="
# Place extra OpenVPN config in here. To configure OpenVPN to use a proxy server,
# uncomment and edit the lines starting with ; below, and replace the parameters
# denoted by square brackets with desired values:

;http-proxy [proxy_address] [proxy_port] [none|basic|ntlm]

# Uncomment and set the below values (in square brackets) if required
;<http-proxy-user-pass>
;[username]
;[password]
;</http-proxy-user-pass>
"
$main_config="
client
config '$ovpn_conf_dir\evon_extra.conf.inc'
config '$ovpn_conf_dir\evon_secrets.conf.inc'
auth-user-pass '$ovpn_conf_dir\evon.uuid'
dev tun
resolv-retry infinite
connect-retry 5 10
nobind
;user nobody
;group nobody
persist-key
persist-tun
remote-cert-tls server
data-ciphers-fallback BF-CBC
verb 3
auth-nocache

<connection>
remote {{ account_domain }}
proto tcp-client
port 443
</connection>
"
$secret_config_encrypted="{{ encrypted_secret_config }}"


### define functions

function IsHostname {
    [OutputType([bool])]
    param([Parameter(Mandatory = $true)] [string]$Hostname)
    return "$Hostname" -match '^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
}


function IsUuid {
    [OutputType([bool])]
    param([Parameter(Mandatory = $true)] [string]$Uuid)
    $ObjectGuid = [System.Guid]::empty
    return [System.Guid]::TryParse($Uuid,[System.Management.Automation.PSReference]$ObjectGuid)
}


function DecryptSecret {
    param(
        [Parameter (Mandatory = $true)] [String]$Apikey,
        [Parameter (Mandatory = $true)] [String]$SecretString
    )
    # encode (equivalent to 'base64' on Linux):
    #   [convert]::ToBase64String((Get-Content -path "openvpn_secrets.conf.aes" -Encoding byte))
    # decode (equivalent to 'base64 -d' on Linux):
    $raw_data =  [char[]][byte[]][Convert]::FromBase64String($SecretString) -join ''
    $boundary = [System.Guid]::NewGuid().ToString(); 
    $LF = "`r`n";
    $bodyLines = ( 
        "--$boundary",
        "Content-Disposition: form-data; name=`"data`"; filename=`"temp.txt`"",
        "Content-Type: application/octet-stream$LF",
        $raw_data,
        "--$boundary--$LF" 
    ) -join $LF
    $url = "https://$account_domain/api/bootstrap/decrypt"
    $headers = @{"Authorization" = "Token $Apikey"}
    $response = (Invoke-RestMethod -Uri $url -Headers $headers -Method Post -ContentType "multipart/form-data; boundary=`"$boundary`"" -Body $bodyLines)
    return $response
}


function InstallOpenVPN {
    write-host Installing OpenVPN...
    $cwd = (Get-Location).Path
    $TempDir = [System.IO.Path]::GetTempPath()
    cd $TempDir
    $release_file="OpenVPN-2.5.7-I602-amd64.msi"
    $url="https://swupdate.openvpn.org/community/releases/$release_file"
    Invoke-WebRequest -Uri $url -OutFile $release_file
    msiexec /i $release_file ADDLOCAL=OpenVPN.Service,OpenVPN,Drivers,Drivers.TAPWindows6,Drivers.Wintun /passive
    cd $cwd
}


function ShowHelp {
    $cmd = $PSCommandPath.replace($PSScriptRoot, ".")
    write-host "Usage:
  $cmd [options]

Options:
  -Apikey <KEY>
    This is the only mandatory option of this script. <KEY> must be the Evon Hub
    API key of the 'deployer' user, or of any superuser. You can obtain the API
    key from the Evon Hub Web UI or CLI using the command: evon --get-deploy-key

  -Uuid <UUID>
    If not set, a unique UUID value will be auto-generated, else <UUID> will be
    used. This value is stored locally and sent to your Evon Hub upon connection
    to identify this server. Evon Hub will map this value to a static, auto-
    assigned IPv4 address on the overlay network. Connecting to Evon Hub using
    the same UUID will cause the server to always be assigned the same static
    IPv4 address. The value will be stored in the file:
    $ovpn_conf_dir\evon.uuid
    Note: If the evon.uuid file exists, the UUID located in that file will always
    be used and this option can not be specified. Remove this file before running
    bootstrap if you want to change the UUID (and the IPv4 overlay net address)
    for this server.

  -Hostname <HOSTNAME>
    If not set, a unique HOSTNAME value will be auto-generated using the output
    of the command 'hostname', else <HOSTNAME> will be used. This value is
    stored locally and sent to your Evon Hub upon connection to provide it with
    the name of this server. This server will then be reachable at the public
    FQDN '<HOSTNAME>.<domain-prefix>.evon.link' where <domain-prefix> is your
    domain prefix that was chosen during registration. Should there be a conflict
    of hostnames on Evon Hub, the HOSTNAME will be auto-indexed, eg. HOSTNAME-1.
    HOSTNAME will be stored in the file $ovpn_conf_dir\evon.uuid
    and can be changed at any time, and applied by restarting the OpenVPN
    service on this server.

  -Extraconf <FILE>
    Append extra OpenVPN config in <FILE> to the default Evon Hub OpenVPN
    config. Use this option if you need to tunnel through a proxy server by
    creating <FILE> with the following contents:

        http-proxy [proxy_address] [proxy_port] [none|basic|ntlm]
        <http-proxy-user-pass>
        [proxy_username]
        [proxy_password]
        </http-proxy-user-pass>

    Refer to the OpenVPN Reference Manual at https://openvpn.net for more info.

  -Uninstall
    Uninstall Evon Bootstrap (stop and unpersist the OpenVPN connection to your
    Evon Hub)

  -Version
    Show version and exit

  -Help
    This help text
"
}

function ShowBanner {
    write-host ''
    write-host '  __| |  |    \ \  | Windows'
    write-host '  _|  \  | () |  \ | Bootstrap'
    write-host " ___|  _/  ___/_| _| v${ver}"
    write-host '[ Elastic Virtual Overlay Network ]'
    write-host ''
}


### main installer

if ( $Help ) {
    ShowBanner
    ShowHelp
    exit 0
}

if ( $Version ) {
    write-host $ver
    exit 0
}

if ( $Uninstall ) {
    write-host Uninstalling...
    write-host Stopping OpenVPN service...
    Stop-Service openvpnservice -ErrorAction SilentlyContinue 
    Set-Service -Name OpenVPNService -StartupType Manual -ErrorAction SilentlyContinue
    write-host Removing Evon config...
    rm -Force $ovpn_conf_dir\evon.ovpn -ErrorAction SilentlyContinue
    rm -Force $ovpn_conf_dir\evon_extra.conf.inc -ErrorAction SilentlyContinue
    rm -Force $ovpn_conf_dir\evon_secrets.conf.inc -ErrorAction SilentlyContinue
    rm -Force $ovpn_conf_dir\evon.uuid -ErrorAction SilentlyContinue
    write-host Done.
    exit 0
}


### set defaults
if ( $Hostname -eq "" ) {
    $Hostname = (hostname)
}
if ( $Uuid -eq "" ) {
    $Uuid = [guid]::NewGuid().toString()
}

### validate params
if ( $Apikey -eq "" ) {
    ShowBanner
    write-host "ERROR: You must provide an API key for the 'deployer' user or any superuser via the -Apikey option. Use -Help for help."
    ShowHelp
    exit 1
}
if ( ! (IsHostname $Hostname) ) {
    throw "Provided Hostname $Hostname is not a valid DNS label. It must conform to RFC 1123."
}
if ( ! (IsUuid $Uuid) ) {
    throw "Provided Uuid $Uuid is not a valid UUIDv4 string. It must conform to RFC 4122."
}

### begin
ShowBanner

### download and install OpenVPN
$ovpn_installed = (get-service | findstr OpenVPNService)
if ( $ovpn_installed -eq $null ) {
    InstallOpenVPN
}
else {
    write-host "OpenVPN already installed."
    write-host "WARNING:"
    write-host "    OpenVPN 2.5.x or higher is required, and must be installed as a Windows Service (GUI is optional but not required)."
    write-host "    If this is not the case this script will fail, however you can manually install OpenVPN and rerun this installer."
    write-host "    If you use OpenVPN to connect to other systems on this machine, you may need to create an extra TAP interface by"
    write-host "    running the following command from the openvpn\bin folder: .\tapctl.exe create"
    start-sleep -seconds 3
}

### Render openvpn configuration
write-host Rendering config...
$secret_config = (DecryptSecret -Apikey $Apikey -SecretString $secret_config_encrypted)
if ( $Extraconf -eq "" ) {
    $extra_config = $extra_config_default
}
else {
    $extra_config = Get-Content $Extraconf
}
$uuid_config = "$Uuid`r`n$Hostname"

# confgure openvpn, write out: main_config, extra_config, secret_config, evon.uuid
write-host Deploying config...
$cwd = (Get-Location).Path
cd $ovpn_conf_dir
"$main_config" | out-file evon.ovpn -Encoding ASCII
"$extra_config" | out-file evon_extra.conf.inc -Encoding ASCII
"$secret_config" | out-file evon_secrets.conf.inc -Encoding ASCII
if ( -not(Test-Path -Path "$ovpn_conf_dir\evon.uuid") ) {
    "$uuid_config" | out-file evon.uuid -Encoding ASCII
}
else {
    write-host Not overwriting existing UUID file: $ovpn_conf_dir\evon.uuid
}
cd $cwd

# start and persist openvpn service
write-host Starting and persisting OpenVPN service...
Set-Service -Name OpenVPNService -StartupType Automatic -ErrorAction SilentlyContinue
Restart-Service OpenVPNService -ErrorAction SilentlyContinue

# test connection
write-host Testing connection...
for ($i = 1 ; $i -le 20; $i++) {
    write-host "."
    Write-Progress -CurrentOperation "Testing connection" ( "Testing connection ... "  )
    $ping_result = ([System.Net.NetworkInformation.Ping]::new().Send("$evon_hub_peer").Status)
    if ( $ping_result -eq "success" ) {
        break
    }
}
Write-Progress -CurrentOperation "Testing connection" ( "Testing connection ... Done"  )
if ( $ping_result -eq "success" ) {
    $ipv4 = (ipconfig | findstr 100.{{ subnet_key }}.2).split(' ')[-1]
    write-host "Success! This server is now connected to your Evon overalay network at IPv4 address $ipv4"
}
else {
    write-host "Error: Unable to contact the Evon Hub VPN peer address at $evon_hub_peer."
    write-host "Please check the OpenVPN log in $pf_dir\OpenVPN\log\evon.log and the configuration files in $ovpn_conf_dir"
    exit 1
}
