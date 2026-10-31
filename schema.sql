-- Esquema PostgreSQL de GO-ya (referencia; la app lo crea con SQLAlchemy)

-- CRM
CREATE TABLE usuario (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  correo VARCHAR(120) UNIQUE NOT NULL,
  rol VARCHAR(20) NOT NULL CHECK (rol IN ('vendedor','consumidor','repartidor','administrador')),
  password_hash VARCHAR(255) NOT NULL,
  documento_estudiante VARCHAR(120) NOT NULL,
  estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','aprobado','rechazado'))
);
CREATE TABLE perfil (
  id SERIAL PRIMARY KEY,
  usuario_id INT UNIQUE NOT NULL REFERENCES usuario(id),
  telefono VARCHAR(30),
  facultad VARCHAR(120) DEFAULT 'Facultad de Ingeniería',
  ubicacion_habitual VARCHAR(160)
);

-- SCM
CREATE TABLE producto (
  id SERIAL PRIMARY KEY,
  vendedor_id INT NOT NULL REFERENCES usuario(id),
  nombre VARCHAR(120) NOT NULL,
  descripcion TEXT NOT NULL,
  foto VARCHAR(120) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  precio NUMERIC(10,2) NOT NULL CHECK (precio >= 0),
  ubicacion_venta VARCHAR(160) NOT NULL
);
CREATE TABLE inventario (
  id SERIAL PRIMARY KEY,
  producto_id INT UNIQUE NOT NULL REFERENCES producto(id),
  cantidad INT NOT NULL DEFAULT 0 CHECK (cantidad >= 0)
);
CREATE TABLE carrito_item (
  id SERIAL PRIMARY KEY,
  usuario_id INT NOT NULL REFERENCES usuario(id),
  producto_id INT NOT NULL REFERENCES producto(id),
  cantidad INT NOT NULL CHECK (cantidad > 0),
  UNIQUE (usuario_id, producto_id)
);

-- ERP
CREATE TABLE orden (
  id SERIAL PRIMARY KEY,
  consumidor_id INT NOT NULL REFERENCES usuario(id),
  repartidor_id INT REFERENCES usuario(id),
  ubicacion_entrega VARCHAR(160) NOT NULL,
  estado VARCHAR(20) NOT NULL DEFAULT 'creada',
  clave_entrega VARCHAR(6) NOT NULL,
  intentos_clave INT NOT NULL DEFAULT 0,
  bloqueo_clave_hasta TIMESTAMP,
  creada_en TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE item_orden (
  id SERIAL PRIMARY KEY,
  orden_id INT NOT NULL REFERENCES orden(id),
  producto_id INT NOT NULL REFERENCES producto(id),
  cantidad INT NOT NULL CHECK (cantidad > 0),
  precio_unitario NUMERIC(10,2) NOT NULL
);
CREATE TABLE factura (
  id SERIAL PRIMARY KEY,
  orden_id INT UNIQUE NOT NULL REFERENCES orden(id),
  folio VARCHAR(20) UNIQUE NOT NULL,
  metodo_pago VARCHAR(30) NOT NULL,
  subtotal NUMERIC(10,2) NOT NULL,
  comision NUMERIC(10,2) NOT NULL,
  total NUMERIC(10,2) NOT NULL,
  emitida_en TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Observer / Notificaciones
CREATE TABLE notificacion (
  id SERIAL PRIMARY KEY,
  usuario_id INT NOT NULL REFERENCES usuario(id),
  orden_id INT NOT NULL REFERENCES orden(id),
  mensaje VARCHAR(255) NOT NULL,
  creada_en TIMESTAMP NOT NULL DEFAULT NOW()
);

-- CRM: solicitudes de cambio de perfil (las resuelve el administrador)
CREATE TABLE solicitud_rol (
  id SERIAL PRIMARY KEY,
  usuario_id INT NOT NULL REFERENCES usuario(id),
  rol_actual VARCHAR(20) NOT NULL,
  rol_solicitado VARCHAR(20) NOT NULL,
  motivo TEXT NOT NULL,
  estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','aprobada','rechazada')),
  creada_en TIMESTAMP NOT NULL DEFAULT NOW(),
  resuelta_en TIMESTAMP
);

-- ERP: evaluaciones de producto y de vendedor (tras recibir el pedido)
CREATE TABLE evaluacion_producto (
  id SERIAL PRIMARY KEY,
  item_orden_id INT UNIQUE NOT NULL REFERENCES item_orden(id),
  producto_id INT NOT NULL REFERENCES producto(id),
  consumidor_id INT NOT NULL REFERENCES usuario(id),
  estrellas INT NOT NULL CHECK (estrellas BETWEEN 1 AND 5),
  comentario VARCHAR(300) NOT NULL DEFAULT '',
  creada_en TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE TABLE evaluacion_vendedor (
  id SERIAL PRIMARY KEY,
  orden_id INT NOT NULL REFERENCES orden(id),
  vendedor_id INT NOT NULL REFERENCES usuario(id),
  consumidor_id INT NOT NULL REFERENCES usuario(id),
  estrellas INT NOT NULL CHECK (estrellas BETWEEN 1 AND 5),
  comentario VARCHAR(300) NOT NULL DEFAULT '',
  creada_en TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (orden_id, vendedor_id)
);
