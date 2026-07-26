---
name: repo-hygiene-scaffold
description: Usar cuando se necesite generar o verificar el .gitignore y el esqueleto de README del repositorio.
---

## Responsabilidad

Generar el `.gitignore` y el esqueleto de `README.md` del repositorio.

## Requerimientos que satisface

- §5 Entregables Esperados del Agente (PRD).
- INV-9 (los directorios de datos no se versionan).

## Entradas

Ninguna: los nombres de directorios de datos (`/bronze`, `/silver`, `/gold`) son fijos por
contrato (REQ-B2, REQ-S3, REQ-G2).

## Salidas

- `.gitignore` en la raíz del repo, excluyendo `/bronze`, `/silver`, `/gold`, entornos virtuales,
  `.env` y artefactos autogenerados de Python.
- `README.md` con secciones: arquitectura, cómo levantar contenedores, cómo ejecutar pruebas,
  cómo visualizar el reporte.

## Invariantes

- INV-9: `/bronze`, `/silver`, `/gold` deben aparecer literalmente en `.gitignore`.

## Procedimiento

1. Escribir `.gitignore` con las exclusiones de datos, entorno y artefactos de Python.
2. Escribir `README.md` con la estructura mínima exigida por §5 del PRD.

## Criterios de aceptación

- `git check-ignore bronze/x.json silver/anime gold/index` no falla (los 3 quedan ignorados).
- `README.md` contiene las 4 secciones exigidas.

## Errores y modos de fallo

- Si `.gitignore` ya existe con reglas propias del usuario, se combinan por append, nunca se
  sobrescribe sin revisar el contenido previo.
