# Changelog

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
