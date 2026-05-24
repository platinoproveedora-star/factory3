# verify_new_factory

Verifica una fabrica generada por `new_factory`.

## Uso

Ejecuta `verify_new_factory` con:

- `factory_dir`: carpeta raiz de la fabrica generada.
- `package_dir`: carpeta base del runtime generado. Default: `factory`.
- `verticals`: verticales esperadas en el registry. Opcional.

Valida estructura, registry, carpetas de skills, carga por `SkillLoader`, `.env.example` generico y ausencia de carpeta legacy `factory` cuando se usa otro `package_dir`.
