# Casa Local Core

Motor local do Casa Local Hub.

## Uso recomendado

Após instalar e iniciar, use **Abrir interface web** na página do App. Esse caminho usa o Ingress do Home Assistant.

A interface permite:

- descobrir equipamentos da rede;
- filtrar e pesquisar;
- renomear dispositivos;
- atribuir ambientes;
- selecionar Português (Brasil), English ou Español;
- preparar credenciais Tuya pelo fluxo protegido do Ingress.

## Estados

**Encontrado** — o aparelho respondeu à descoberta.

**Chave local necessária** — o protocolo foi identificado, mas falta uma credencial local.

**Local pronto** — a credencial foi validada diretamente com o aparelho.

## Segurança

O Casa Local Core mantém dados persistentes em `/data`. Credenciais são criptografadas antes de serem armazenadas.

A porta `8799` existe para desenvolvimento e comunicação local. Não exponha essa porta na Internet.

## API de desenvolvimento

- `GET /health`
- `GET /api/v1/status`
- `GET /api/v1/devices`
- `POST /api/v1/discovery`
- `PATCH /api/v1/devices/{stable_id}`

O endpoint de credenciais Tuya é restrito ao Home Assistant Ingress.


## Controle local Tuya

Após validar uma chave local, o Casa Local Core lê os DPS e identifica, por heurística, o tipo provável do dispositivo. Nenhum comando é enviado durante essa identificação.

Quando um DPS booleano é reconhecido como controle principal, a interface disponibiliza **Ligar/Desligar**. O usuário precisa acionar o comando explicitamente.
