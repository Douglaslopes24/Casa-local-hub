# Casa Local Hub

**Sua casa. Seu controle. Local.**

Casa Local Hub é uma plataforma local-first para descobrir, organizar e preparar dispositivos de automação residencial para uso local com Home Assistant.

> **v0.4.1 — experimental.** Use apenas em uma rede local confiável.

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

- **v0.4.x:** integração Home Assistant, pareamento e entidades locais.
- **v0.5:** câmeras ONVIF/RTSP e entidades de câmera.
- **v0.6:** aplicativo Android e provisionamento guiado.
- **v0.5:** aplicativo Android e provisionamento guiado.


## Controle Tuya

Depois que uma `local_key` é validada, o Core lê o status do aparelho, analisa os DPS sem enviar comandos e identifica controles booleanos prováveis. A interface só envia um comando quando o usuário toca explicitamente em **Ligar** ou **Desligar**.

O estado pode ser atualizado manualmente pelo painel. DPS não identificados como booleanos não são alterados automaticamente.


## Integração com o Home Assistant

O mesmo repositório também contém a integração personalizada `casa_local_hub`.

### Instalação recomendada com HACS

1. No HACS, adicione este repositório como **Custom repository** do tipo **Integration**.
2. Instale **Casa Local Hub**.
3. Reinicie o Home Assistant.
4. Vá em **Configurações → Dispositivos e serviços → Adicionar integração → Casa Local Hub**.
5. No painel do Casa Local Core, use **Conectar ao Home Assistant** para gerar um código temporário.
6. Informe o endereço do Core e o código de 8 dígitos.

Quando Core e integração rodam no mesmo Home Assistant, tente primeiro `http://127.0.0.1:8799`. Se o ambiente não compartilhar a rede do host, use o endereço LAN do Home Assistant seguido de `:8799`.

O código é de uso único e expira em 5 minutos. A integração recebe um token próprio; ela não recebe nem lê as `local_key` armazenadas no cofre.

### Entidades atuais

Dispositivos Tuya com status **Local pronto** podem aparecer automaticamente como:

- `switch` para tomadas/interruptores identificados;
- `light` para lâmpadas identificadas.

O estado é consultado localmente e os comandos passam pelo Casa Local Core.


## Fluxo de validação

O Casa Local Hub segue esta ordem antes de expor qualquer dispositivo ao Home Assistant:

1. **Buscar** — encontra o equipamento na rede local.
2. **Validar comunicação** — comprova que o Core consegue ler o aparelho localmente.
3. **Validar controle** — o usuário envia conscientemente um comando de teste e o Core confirma o estado retornado.
4. **Integrar** — somente então o aparelho fica disponível para a integração do Home Assistant.

Encontrar um dispositivo ou possuir uma `local_key` válida não é suficiente para chamá-lo de compatível. O status **Dispositivo validado** só é concedido após confirmação real de controle local.
