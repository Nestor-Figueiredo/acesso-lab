# ===========================================================================
# SSH forwarding WSL2 -> Windows  (roda NO WINDOWS, PowerShell como Admin)
# ===========================================================================
# WSL2 tem NAT própria: o sshd roda DENTRO do WSL, mas o notebook do aluno
# na rede da escola não "enxerga" o IP interno do WSL para conexões de fora.
# Solução: encaminhar a porta 22 do Windows para o IP do WSL2 via netsh.
#
# Como usar:
#   - Abra o PowerShell como Administrador
#   - Rode:  powershell -ExecutionPolicy Bypass -File scripts/ssh_forward_wsl2.ps1
#   - O comando abaixo é o que ele executa (para referência rápida)
# ===========================================================================

# 1) Descobrir o IP do WSL2 (rode DENTRO do WSL):
#    hostname -I  -> ex: 172.20.x.x
#    Rode dentro do WSL: ip addr show eth0 | grep inet

# 2) No PowerShell (Admin), encaminhar a porta 22 do Windows para o IP do WSL2:
$wsl_ip = "172.20.0.2"   # TROQUE pelo IP real do seu WSL2 (hostname -I)
netsh interface portproxy add v4tov4 listenport=22 listenaddress=0.0.0.0 connectport=22 connectaddress=$wsl_ip

# 3) Liberar a porta 22 no Firewall do Windows (admin):
netsh advfirewall firewall add rule name="SSH-WSL2" dir=in action=allow protocol=TCP localport=22

# 4) Ver o encaminhamento ativo:
netsh interface portproxy show v4tov4

Write-Host "Pronto. Aluno acessa: ssh aluno@<IP_DO_WINDOWS/SERVIDOR>"

# ---------------------------------------------------------------------------
# OBS: O IP do WSL2 MUDOU A CADA REBOOT do Windows (WSL2 usa DHCP interno).
# Para tornar fixo, configurar no .wslconfig do Windows (na pasta do usuário):
#
#   [wsl2]
#   networkingMode=mirrored        # Win11 22H2+: rede compartilha IP do host
#
# OU criar uma entrada netstat estática no PowerShell APÓS cada boot.
# Com networkingMode=mirrored, o WSL usa o MESMO IP do Windows e o forwarding
# nem é necessário (os alunos acessam o IP da máquina direto).
# ---------------------------------------------------------------------------
