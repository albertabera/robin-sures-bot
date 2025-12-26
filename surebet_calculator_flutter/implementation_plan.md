# Plan de Implementación: Surebet Calculator (Flutter App)

Este documento detalla el plan paso a paso para desarrollar la calculadora de "Surebets" (apuestas seguras) como una aplicación móvil nativa utilizando **Flutter**.

## 1. Configuración del Proyecto e Infraestructura
- [ ] **Inicialización**: Crear el proyecto Flutter (`flutter create surebet_calculator`).
- [ ] **Limpieza**: Eliminar el código "boilerplate" inicial.
- [ ] **Estructura de Carpetas**: Configurar una estructura escalable (ej. Clean Architecture o Feature-first).
  - `lib/core` (configuraciones, temas, utilidades)
  - `lib/features/calculator` (lógica y UI de la calculadora)
  - `lib/shared` (widgets reutilizables)
- [ ] **Dependencias**: Agregar paquetes esenciales en `pubspec.yaml`:
  - `flutter_riverpod` (Gestión de estado)
  - `go_router` (Navegación)
  - `google_fonts` (Tipografía premium)
  - `intl` (Formateo de moneda y números)

## 2. Diseño UI/UX (Estética Premium)
Siguiendo las instrucciones de diseño de alto nivel:
- [ ] **Tema Global**: Definir `ThemeData` con colores vibrantes y modo oscuro (Dark Mode) moderno.
  - Paleta de colores: Tonos oscuros profundos (ej. Gunmetal, Charcoal) con acentos neón (ej. Electric Blue, Lime Green) para las acciones principales.
- [ ] **Tipografía**: Implementar fuentes modernas como *Inter* o *Outfit* mediante `google_fonts`.
- [ ] **Componentes Personalizados**:
  - `NeoInput`: Campos de texto estilizados con bordes suaves y efectos de foco.
  - `GradientButton`: Botones con gradientes y micro-animaciones al presionar.
  - `ResultCard`: Tarjeta con efecto de "glassmorphism" (fondo borroso) para mostrar los resultados.

## 3. Lógica de Negocio (Core)
- [ ] **Modelo de Datos**: Crear clase `SurebetCalculation` que contenga:
  - Cuotas (Odds) para Opción A y Opción B (y opcionalmente Empate).
  - Monto total a apostar.
- [ ] **Lógica de Cálculo**:
  - Función para calcular el porcentaje de arbitraje.
  - Función para calcular cuánto apostar en cada opción para garantizar ganancia.
  - Función para calcular el beneficio neto.
- [ ] **Gestión de Estado**:
  - Crear un `StateNotifier` o `Provider` con Riverpod para manejar los inputs del usuario y actualizar los resultados en tiempo real.

## 4. Desarrollo de Pantallas
- [ ] **Pantalla Principal (CalculatorScreen)**:
  - Header atractivo con título y botón de configuración/info.
  - Formulario de entrada para las cuotas (Odds) y el "Stake" (inversión total).
  - Selector de tipo de evento (2 opciones vs 3 opciones).
  - Sección de resultados dinámica (aparece o se actualiza automáticamente al escribir).
- [ ] **Pantalla de Detalles/Ayuda (Opcional)**:
  - Explicación de qué es una Surebet.
  - Instrucciones de uso.

## 5. Refinamiento y Pruebas
- [ ] **Validación**: Asegurar que no se permitan valores negativos o inválidos (0.0).
- [ ] **Animaciones**: Agregar transiciones suaves entre cambios de estado (ej. cuando aparecen los resultados).
- [ ] **Icono de App**: Configurar el icono de la aplicación (`flutter_launcher_icons`).
- [ ] **Pruebas Manuales**: Verificar el funcionamiento en simuladores iOS y Android.

## 6. Construcción
- [ ] Generar APK/AAB para Android.
- [ ] Generar Runner.app para iOS (si se dispone de entorno Mac).
