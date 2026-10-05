# Casa Local Hub

**Sua casa. Seu controle. Local.**

Casa Local Hub é uma plataforma local-first para descobrir, organizar e preparar dispositivos de automação residencial para uso local com Home Assistant.

> **v0.3.0 — experimental.** Use apenas em uma rede local confiável.

## Instalação

No Home Assistant, abra **Configurações → Apps → Loja de Apps** e adicione este repositório:

`https://github.com/Douglaslopes24/Casa-local-hub`

Depois procure por **Casa Local Core**, instale e inicie.

A partir da v0.2.0, o App oferece **Ingress**. Prefira abrir pelo botão **Abrir interface web** dentro do Home Assistant.

## Interface

O painel inclui:

- Português (Brasil), English e Español.
- Busca e filtros de dispositivos.
- Nome amigável e ambiente.
- Persistência local em SQLite.
- Estados simplificados: encontrado, precisa de chave e local pronto.

## Protocolos iniciais

- Tuya/OEM — descoberta LAN e validação de `local_key`.
- Sonoff/eWeLink — descoberta mDNS.
- Câmeras — descoberta ONVIF via WS-Discovery.

Descobrir um dispositivo não significa afirmar compatibilidade. O Casa Local Hub só mostra **Local pronto** depois de validar o caminho local.

## Segurança

- Credenciais não são gravadas em texto puro.
- O cofre usa criptografia local e chave mestra armazenada em `/data` dentro do App.
- Cadastro de credenciais Tuya é aceito apenas via Home Assistant Ingress.
- Não faça port-forward da porta 8799 para a Internet.
- Chaves locais nunca são retornadas pela API.

## Roadmap

- **v0.3.x:** identificação de DPS e controle local Tuya.
- **v0.4:** integração Home Assistant com entidades.
- **v0.5:** aplicativo Android e provisionamento guiado.
- **v0.5:** aplicativo Android e provisionamento guiado.


## Controle Tuya

Depois que uma `local_key` é validada, o Core lê o status do aparelho, analisa os DPS sem enviar comandos e identifica controles booleanos prováveis. A interface só envia um comando quando o usuário toca explicitamente em **Ligar** ou **Desligar**.

O estado pode ser atualizado manualmente pelo painel. DPS não identificados como booleanos não são alterados automaticamente.
