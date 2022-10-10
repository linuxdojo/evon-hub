#!/usr/bin/pwsh
$url = "https://xxxxx.evon.link/api/server"
$auth_token = "xxx"
write-host "IPv4           `t State`t FQDN"
while ( $url -ne $null ) {
    $response = Invoke-RestMethod -Uri $url -Headers @{"Authorization" = "Token $auth_token"}
    foreach ( $server in $response.results ) {
        $state = if ($server.connected) {"up"} else {"down"}
        write-host $server.ipv4_address `t $state `t $server.fqdn
    }
    $url = $response.next
}
