// Espejo en frontend del flag DEMO_MODE del backend.
//
// El docker-compose pasa `NEXT_PUBLIC_DEMO_MODE` al frontend (lee la env
// DEMO_MODE del .env del backend). Si está activo, el wizard muestra
// botones "Cargar ejemplo" en pasos 1, 3 y 4. Si no, los botones no
// se renderizan — el binario de producción no incluye datos demo y los
// endpoints /api/v1/demo/* devuelven 404.

export const isDemoMode: boolean = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
