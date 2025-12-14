# Savant_Lab

## Lab

TODO: Describe the lab process.

### CI y secreto requerido

El workflow `.github/workflows/savant_lab_gate.yml` espera que exista un secret de
repositorio llamado `SAVANT_BASE_URL` con la URL base del API de Savant. Si el
secret no está definido, la ejecución usa como respaldo público
`https://antonypamo-apisavant2.hf.space` e imprime un aviso en los logs de CI.
