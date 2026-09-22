GOya

GO-ya es una plataforma de negocios electrónicos y logística desarrollada para la comunidad de la Facultad de Ingeniería (UNAM). El sistema conecta de forma eficiente a vendedores locales, consumidores y repartidores dentro del campus, gestionando todo el ciclo de vida de las órdenes y pagos.

El ecosistema de GO-ya clasifica a los usuarios en tres perfiles principales:
* **Vendedor:** Registra productos, establece precios/cantidades y define su ubicación de venta.
* **Consumidor:** Explora productos, genera órdenes y define su ubicación de entrega.
* **Repartidor:** Se enlaza a las órdenes generadas para conectar la ubicación del vendedor con la del consumidor.

* **Patrón Observer:** Implementado en el núcleo del sistema para notificar de manera automática a los actores involucrados sobre cualquier cambio en el estado de una `ORDEN` (ej. preparación, en camino, entregado).
* **Gestión de Datos:** Modelado relacional que centraliza la lógica de las órdenes, desglosando la información de cada transacción en entidades de `PAGO` (método, comisión) y `PRODUCTO`.

Stack Tecnológico (Propuesto)
* **Backend:** Python (API REST)
* **Frontend:** HTML5, CSS 
* **Base de Datos:** PostgreSQL
* **Patrón Principal:** Observer
