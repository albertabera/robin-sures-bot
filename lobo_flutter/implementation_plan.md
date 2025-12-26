# Plan de Implementación - App "El Lobo" 🐺

## Visión General
App móvil (Android/iOS) para jugar al juego de "El Lobo" (Werewolf/Mafia) en modo offline (fiesta).
La app gestiona:
- Asignación de roles (secreta, pasando el móvil).
- Narración de la partida (fases día/noche).
- Temporizadores y eventos.
- Monetización vía Anuncios y Suscripción Premium.

## Estética
- **Tema**: Oscuro, Misterioso, Noche.
- **Colores**: Morados profundos, Negros, Acentos Neón (Cian/Magenta), Texto claro.
- **Vibe**: Premium, fluido, animado.

## Fases del Desarrollo

### Fase 1: Fundamentos y Diseño (ACTUAL)
- [x] Inicializar proyecto Flutter & Estructura de carpetas.
- [ ] Configurar Dependencias Core (Riverpod, Router, Google Fonts).
- [ ] Implementar Sistema de Diseño `AppTheme` (Colores, Tipografía).
- [ ] Pantalla de "Splash/Home" con estética premium.

### Fase 2: Configuración de Partida
- [ ] Selector de número de jugadores.
- [ ] Configuración de Roles (cuántos Lobos, Aldeanos, Bruja, Vidente, etc.).
- [ ] Pantalla de entrada de nombres (opcional) o asignación numérica.

### Fase 3: Asignación de Roles (El "Pase")
- [ ] Mecánica de "Pasar el móvil".
- [ ] Pantalla "Toca para ver tu carta".
- [ ] Animación de revelación de carta (Flip card).
- [ ] Confirmación y "Pasa al siguiente".

### Fase 4: El Core del Juego (Narrador)
- [ ] Loop del juego: Noche -> Día -> Votación.
- [ ] **Noche**:
    - Turno de Lobos (seleccionar víctima).
    - Turno de Roles Especiales (Bruja, Vidente, etc.).
- [ ] **Día**:
    - Revelación de eventos nocturnos.
    - Temporizador de debate.
    - Votación de eliminación.
- [ ] Pantalla de "Victoria" (Lobos o Aldeanos).

### Fase 5: Monetización y Pulido
- [ ] Integrar RevenueCat (Suscripciones).
- [ ] Integrar AdMob (Anuncios intersticiales entre partidas).
- [ ] Ajustes de sonido (Ambiente, efectos).
- [ ] Animaciones y transiciones finales.
