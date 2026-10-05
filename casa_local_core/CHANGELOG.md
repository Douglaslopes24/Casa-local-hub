# Changelog

## 0.5.0

- Suporte ao Casa Local Hub App para Android.
- Anúncio mDNS `_casalocal._tcp` para descoberta automática do Core.
- Pareamento específico do aplicativo antes da validação dos dispositivos.
- Endpoint autenticado para o aplicativo listar todos os dispositivos.
- Chave RSA própria do Core persistida em `/data`.
- Credenciais Tuya enviadas pelo celular com RSA-OAEP + AES-256-GCM.
- Access ID e Access Secret são usados apenas em memória e não são persistidos.
- Sincronização Tuya Cloud busca local_key e grava diretamente no cofre criptografado.
- local_key não é devolvida ao aplicativo.
- Validação de comunicação local automática após a sincronização.

## 0.4.1

- Fluxo obrigatório: Buscar → Validar → Integrar.
- Uma local_key válida comprova comunicação local, não controle.
- Dispositivo só fica pronto após comando explícito confirmado por leitura de estado.
- Dispositivos antigos são migrados para a nova semântica de validação.
- Pareamento com Home Assistant é bloqueado até existir ao menos um dispositivo validado.
- A integração recebe somente dispositivos marcados como integráveis.
- Painel diferencia comunicação validada de controle validado.

## 0.4.0

- Pareamento seguro entre Casa Local Core e integração Home Assistant.
- Código temporário de 8 dígitos, válido por 5 minutos.
- Tokens persistidos apenas como hash no Core.
- Integração `casa_local_hub` com config flow pela interface.
- Entidades Tuya `switch` e `light` para dispositivos Local pronto.
- Atualização coordenada de estado local a cada 20 segundos.
- Criação dinâmica de novas entidades compatíveis.
- Traduções Português (Brasil), English e Español.
- Estrutura pronta para instalação como repositório personalizado no HACS.

## 0.3.0

- Leitura local de estado Tuya após validação da chave.
- Análise segura dos DPS sem enviar comandos durante a identificação.
- Identificação provável de interruptores/tomadas e lâmpadas.
- Controle explícito Ligar/Desligar para DPS booleanos validados.
- Atualização manual de estado pelo painel.
- Persistência do perfil Tuya e último estado conhecido.
- Testes automatizados para classificação de DPS.

## 0.2.0

- Novo painel visual responsivo.
- Português (Brasil), English e Español.
- Acesso integrado pelo Home Assistant Ingress.
- Dispositivos encontrados persistem em SQLite.
- Nome e ambiente personalizados por dispositivo.
- Cofre local criptografado para credenciais.
- Validação segura de `local_key` Tuya somente via Ingress.
- Filtros, busca e estados simplificados.

## 0.1.4

- Correção de cache da interface.

## 0.1.x

- Primeira descoberta Tuya, Sonoff/eWeLink e ONVIF.
