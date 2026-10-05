# Casa Local Hub

**Sua casa. Seu controle. Local.**

Casa Local Hub é uma plataforma local-first para descobrir e integrar dispositivos de automação residencial ao Home Assistant com a menor dependência possível de nuvem.

> **v0.1.1 — experimental.** Use apenas em uma rede local confiável.

## Instalação do Casa Local Core

No Home Assistant, abra **Configurações → Apps → Loja de Apps**, adicione este repositório:

`https://github.com/Douglaslopes24/Casa-local-hub`

Depois atualize a loja, abra **Casa Local Core**, instale e inicie.

Quando estiver rodando, teste:

`http://IP_DO_HOME_ASSISTANT:8799/health`

A porta 8799 é destinada somente à rede local. Não faça port-forward dela para a Internet.

## Protocolos iniciais

- Tuya/OEM — descoberta LAN.
- Sonoff/eWeLink — descoberta mDNS.
- Câmeras — descoberta ONVIF via WS-Discovery.

Descobrir um dispositivo não significa afirmar compatibilidade. O Casa Local Hub só deverá mostrar **Local pronto** depois de validar o controle local.

## Roadmap

- **v0.1.x:** descoberta e estabilidade.
- **v0.2:** identidade do hub, QR Code e pareamento autenticado.
- **v0.3:** controle local Tuya/Sonoff e ONVIF/RTSP.
- **v0.4:** aplicativo Android.
- **v0.5:** experiência Home Assistant completa.
