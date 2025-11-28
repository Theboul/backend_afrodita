from datetime import date
from typing import Any, Dict, List

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncYear

from apps.ventas.models import DetalleVenta, Venta
from apps.usuarios.models import Cliente
from apps.envio.models import Envio
from apps.inventario.models import Inventario
from apps.promocion.models import Promocion
from apps.bitacora.models import Bitacora


class NoDataForReport(Exception):
    """Se lanza cuando no existen datos para el reporte solicitado."""


class ReportType:
    VENTAS = "VENTAS"
    CLIENTES = "CLIENTES"
    ENVIOS = "ENVIOS"
    PRODUCTOS_MAS_VENDIDOS = "PRODUCTOS_MAS_VENDIDOS"
    INVENTARIO = "INVENTARIO"
    PROMOCIONES = "PROMOCIONES"
    BITACORA = "BITACORA"

    @classmethod
    def choices(cls) -> List[tuple[str, str]]:
        return [
            (cls.VENTAS, "Ventas diarias/mensuales/anuales"),
            (cls.CLIENTES, "Clientes registrados"),
            (cls.ENVIOS, "Envíos realizados"),
            (cls.PRODUCTOS_MAS_VENDIDOS, "Productos más vendidos"),
            (cls.INVENTARIO, "Reporte de inventario"),
            (cls.PROMOCIONES, "Promociones activas o expiradas"),
            (cls.BITACORA, "Eventos de bitácora"),
        ]


class Frequency:
    DIARIO = "DIARIO"
    MENSUAL = "MENSUAL"
    ANUAL = "ANUAL"

    @classmethod
    def choices(cls) -> List[tuple[str, str]]:
        return [
            (cls.DIARIO, "Diario"),
            (cls.MENSUAL, "Mensual"),
            (cls.ANUAL, "Anual"),
        ]


class ReportesService:
    """Servicio centralizado para generación de reportes."""

    @staticmethod
    def generar_reporte(tipo_reporte: str, filtros: Dict[str, Any]) -> Dict[str, Any]:
        if tipo_reporte == ReportType.VENTAS:
            return ReportesService._reporte_ventas_v2(filtros)
        if tipo_reporte == ReportType.CLIENTES:
            return ReportesService._reporte_clientes_v2(filtros)
        if tipo_reporte == ReportType.ENVIOS:
            return ReportesService._reporte_envios(filtros)
        if tipo_reporte == ReportType.PRODUCTOS_MAS_VENDIDOS:
            return ReportesService._reporte_productos_mas_vendidos(filtros)
        if tipo_reporte == ReportType.INVENTARIO:
            return ReportesService._reporte_inventario(filtros)
        if tipo_reporte == ReportType.PROMOCIONES:
            return ReportesService._reporte_promociones(filtros)
        if tipo_reporte == ReportType.BITACORA:
            return ReportesService._reporte_bitacora(filtros)

        raise ValueError("Tipo de reporte no soportado.")

    @staticmethod
    def _aplicar_rango_fechas(queryset, field_name: str, filtros: Dict[str, Any]):
        fecha_desde = filtros.get("fecha_desde")
        fecha_hasta = filtros.get("fecha_hasta")

        if fecha_desde:
            queryset = queryset.filter(**{f"{field_name}__gte": fecha_desde})
        if fecha_hasta:
            queryset = queryset.filter(**{f"{field_name}__lte": fecha_hasta})
        return queryset

    @staticmethod
    def _reporte_ventas_v2(filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reporte de ventas detallado por venta, con serie agregada
        para gr��fico por per��odo.
        """
        frecuencia = filtros.get("frecuencia") or Frequency.MENSUAL

        qs = Venta.objects.select_related(
            "id_cliente__id_cliente",
            "id_metodo_pago",
        )
        qs = ReportesService._aplicar_rango_fechas(qs, "fecha", filtros)

        # Filtro por m��todo de pago (id)
        metodo_pago_id = filtros.get("id_metodo_pago")
        if metodo_pago_id:
            qs = qs.filter(id_metodo_pago_id=metodo_pago_id)

        # Filtro por cliente: por id o por nombre completo
        cliente_query = (filtros.get("cliente") or "").strip()
        if cliente_query:
            condiciones = Q(
                id_cliente__id_cliente__nombre_completo__icontains=cliente_query
            ) | Q(
                id_cliente__id_cliente__nombre_usuario__icontains=cliente_query
            )
            if cliente_query.isdigit():
                condiciones |= Q(id_cliente_id=int(cliente_query))
            qs = qs.filter(condiciones)

        if not qs.exists():
            raise NoDataForReport("No existen ventas para el per��odo indicado.")

        # Serie para gr��fico: agregados por per��odo
        if frecuencia == Frequency.DIARIO:
            trunc = TruncDate("fecha")
            formato = "%Y-%m-%d"
        elif frecuencia == Frequency.ANUAL:
            trunc = TruncYear("fecha")
            formato = "%Y"
        else:
            trunc = TruncMonth("fecha")
            formato = "%Y-%m"

        agregados = (
            qs.annotate(periodo=trunc)
            .values("periodo")
            .annotate(
                total_ventas=Count("id_venta"),
                monto_total=Sum("monto_total"),
            )
            .order_by("periodo")
        )

        total_ventas = qs.count()
        monto_total = qs.aggregate(total=Sum("monto_total"))["total"] or 0

        serie_grafico = [
            {
                "etiqueta": row["periodo"].strftime(formato)
                if row["periodo"]
                else None,
                "total_ventas": row["total_ventas"],
                "monto_total": row["monto_total"],
            }
            for row in agregados
        ]

        # Resultados detallados por venta
        resultados: List[Dict[str, Any]] = []
        for venta in qs.order_by("-fecha", "-id_venta"):
            usuario_cliente = getattr(venta.id_cliente, "id_cliente", None)
            nombre_cliente = (
                usuario_cliente.nombre_completo if usuario_cliente else None
            )
            estado_venta = venta.estado.upper()
            if "ANUL" in estado_venta:
                estado_venta = "ANULADO"
            elif "COMP" in estado_venta:
                estado_venta = "COMPLETADO"

            resultados.append(
                {
                    "id_venta": venta.id_venta,
                    "fecha": venta.fecha,
                    "monto_total": venta.monto_total,
                    "estado_venta": estado_venta,
                    "metodo_pago": getattr(venta.id_metodo_pago, "tipo", None),
                    "id_cliente": venta.id_cliente_id,
                    "nombreCompleto_cliente": nombre_cliente,
                }
            )

        return {
            "tipo_reporte": ReportType.VENTAS,
            "filtros": filtros,
            "resumen": {
                "total_ventas": total_ventas,
                "monto_total": monto_total,
                "serie_grafico": {
                    "tipo": "linea",
                    "eje_x": "Periodo",
                    "eje_y": "Monto total",
                    "puntos": serie_grafico,
                },
            },
            "resultados": resultados,
        }

    @staticmethod
    def _reporte_ventas(filtros: Dict[str, Any]) -> Dict[str, Any]:
        frecuencia = filtros.get("frecuencia") or Frequency.MENSUAL

        qs = Venta.objects.all()
        qs = ReportesService._aplicar_rango_fechas(qs, "fecha", filtros)

        if not qs.exists():
            raise NoDataForReport("No existen ventas para el período indicado.")

        if frecuencia == Frequency.DIARIO:
            trunc = TruncDate("fecha")
            formato = "%Y-%m-%d"
        elif frecuencia == Frequency.ANUAL:
            trunc = TruncYear("fecha")
            formato = "%Y"
        else:
            trunc = TruncMonth("fecha")
            formato = "%Y-%m"

        agregados = (
            qs.annotate(periodo=trunc)
            .values("periodo")
            .annotate(
                total_ventas=Count("id_venta"),
                monto_total=Sum("monto_total"),
            )
            .order_by("periodo")
        )

        resultados: List[Dict[str, Any]] = []
        total_ventas = 0
        monto_total = 0

        for row in agregados:
            periodo = row["periodo"]
            total_ventas += row["total_ventas"]
            monto_total += row["monto_total"] or 0
            resultados.append(
                {
                    "periodo": periodo.strftime(formato) if periodo else None,
                    "total_ventas": row["total_ventas"],
                    "monto_total": row["monto_total"],
                }
            )

        return {
            "tipo_reporte": ReportType.VENTAS,
            "filtros": filtros,
            "resumen": {
                "total_ventas": total_ventas,
                "monto_total": monto_total,
            },
            "resultados": resultados,
        }

    @staticmethod
    def _reporte_clientes_v2(filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reporte de clientes registrados, detallado por cliente y con
        serie de nuevos clientes por fecha para el gr��fico.
        """
        qs = Cliente.objects.select_related("id_cliente")

        fecha_desde = filtros.get("fecha_desde")
        fecha_hasta = filtros.get("fecha_hasta")

        if fecha_desde:
            qs = qs.filter(id_cliente__fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(id_cliente__fecha_registro__date__lte=fecha_hasta)

        if not qs.exists():
            raise NoDataForReport("No existen clientes para el per��odo indicado.")

        agregados = (
            qs.annotate(fecha=TruncDate("id_cliente__fecha_registro"))
            .values("fecha")
            .annotate(total=Count("id_cliente"))
            .order_by("fecha")
        )

        serie_grafico = [
            {
                "etiqueta": row["fecha"].strftime("%Y-%m-%d") if row["fecha"] else None,
                "total": row["total"],
            }
            for row in agregados
        ]

        total_clientes = qs.count()

        resultados = list(
            qs.values(
                "id_cliente_id",
                "id_cliente__nombre_completo",
                "id_cliente__nombre_usuario",
                "id_cliente__correo",
                "id_cliente__fecha_registro",
            ).order_by("id_cliente__nombre_completo", "id_cliente_id")
        )

        return {
            "tipo_reporte": ReportType.CLIENTES,
            "filtros": filtros,
            "resumen": {
                "total_clientes": total_clientes,
                "serie_grafico": {
                    "tipo": "barra",
                    "eje_x": "Fecha registro",
                    "eje_y": "Nuevos clientes",
                    "puntos": serie_grafico,
                },
            },
            "resultados": resultados,
        }

    @staticmethod
    def _reporte_clientes(filtros: Dict[str, Any]) -> Dict[str, Any]:
        qs = Cliente.objects.select_related("id_cliente")

        fecha_desde = filtros.get("fecha_desde")
        fecha_hasta = filtros.get("fecha_hasta")

        if fecha_desde:
            qs = qs.filter(id_cliente__fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(id_cliente__fecha_registro__date__lte=fecha_hasta)

        if not qs.exists():
            raise NoDataForReport("No existen clientes para el período indicado.")

        agregados = (
            qs.annotate(fecha=TruncDate("id_cliente__fecha_registro"))
            .values("fecha")
            .annotate(total=Count("id_cliente"))
            .order_by("fecha")
        )

        total_clientes = qs.count()
        resultados = [
            {
                "fecha": row["fecha"].strftime("%Y-%m-%d") if row["fecha"] else None,
                "total_registrados": row["total"],
            }
            for row in agregados
        ]

        return {
            "tipo_reporte": ReportType.CLIENTES,
            "filtros": filtros,
            "resumen": {
                "total_clientes": total_clientes,
            },
            "resultados": resultados,
        }

    @staticmethod
    def _reporte_envios(filtros: Dict[str, Any]) -> Dict[str, Any]:
        qs = Envio.objects.select_related("cod_tipo_envio")
        qs = ReportesService._aplicar_rango_fechas(qs, "fecha_envio", filtros)

        estado_envio = filtros.get("estado_envio")
        if estado_envio:
            qs = qs.filter(estado_envio=estado_envio)

        if not qs.exists():
            raise NoDataForReport("No existen envíos para el período indicado.")

        agregados = (
            qs.values("estado_envio", "cod_tipo_envio__tipo")
            .annotate(
                cantidad=Count("cod_envio"),
                costo_total=Sum("costo"),
            )
            .order_by("estado_envio", "cod_tipo_envio__tipo")
        )

        total_envios = qs.count()
        costo_total = qs.aggregate(total=Sum("costo"))["total"] or 0

        resultados = [
            {
                "estado_envio": row["estado_envio"],
                "tipo_envio": row["cod_tipo_envio__tipo"],
                "cantidad": row["cantidad"],
                "costo_total": row["costo_total"],
            }
            for row in agregados
        ]

        return {
            "tipo_reporte": ReportType.ENVIOS,
            "filtros": filtros,
            "resumen": {
                "total_envios": total_envios,
                "costo_total": costo_total,
                "serie_grafico": {
                    "tipo": "barra",
                    "eje_x": "Estado",
                    "eje_y": "Cantidad",
                    "puntos": [
                        {
                            "etiqueta": f"{row['estado_envio']} - {row['cod_tipo_envio__tipo']}",
                            "total": row["cantidad"],
                        }
                        for row in agregados
                    ],
                },
            },
            "resultados": resultados,
        }

    @staticmethod
    def _reporte_productos_mas_vendidos(filtros: Dict[str, Any]) -> Dict[str, Any]:
        top = filtros.get("top") or 10

        qs = DetalleVenta.objects.select_related("id_producto", "id_venta")
        qs = ReportesService._aplicar_rango_fechas(qs, "id_venta__fecha", filtros)

        if not qs.exists():
            raise NoDataForReport("No existen ventas de productos para el período indicado.")

        agregados = (
            qs.values("id_producto", "id_producto__nombre")
            .annotate(
                cantidad_total=Sum("cantidad"),
                monto_total=Sum("sub_total"),
            )
            .order_by("-cantidad_total")[:top]
        )

        resultados = [
            {
                "id_producto": row["id_producto"],
                "nombre_producto": row["id_producto__nombre"],
                "cantidad_vendida": row["cantidad_total"],
                "monto_total": row["monto_total"],
            }
            for row in agregados
        ]

        total_productos = len(resultados)

        return {
            "tipo_reporte": ReportType.PRODUCTOS_MAS_VENDIDOS,
            "filtros": filtros,
            "resumen": {
                "total_productos": total_productos,
                "serie_grafico": {
                    "tipo": "barra",
                    "eje_x": "Producto",
                    "eje_y": "Cantidad vendida",
                    "puntos": [
                        {
                            "etiqueta": row["nombre_producto"],
                            "total": row["cantidad_vendida"],
                        }
                        for row in resultados
                    ],
                },
            },
            "resultados": resultados,
        }

    @staticmethod
    def _reporte_inventario(filtros: Dict[str, Any]) -> Dict[str, Any]:
        qs = Inventario.objects.select_related("producto")

        solo_stock_bajo = filtros.get("solo_stock_bajo")
        if solo_stock_bajo:
            # Requerimiento: stock bajo si cantidad_actual <= 10
            qs = qs.filter(cantidad_actual__lte=10)

        if not qs.exists():
            raise NoDataForReport("No existen registros de inventario para los filtros indicados.")

        resultados = list(
            qs.values(
                "producto__id_producto",
                "producto__nombre",
                "cantidad_actual",
                "ubicacion",
            ).order_by("producto__nombre")
        )

        total_items = qs.count()
        con_stock_bajo = qs.filter(cantidad_actual__lte=10).count()

        return {
            "tipo_reporte": ReportType.INVENTARIO,
            "filtros": filtros,
            "resumen": {
                "total_items": total_items,
                "items_con_stock_bajo": con_stock_bajo,
                "serie_grafico": {
                    "tipo": "barra",
                    "eje_x": "Producto",
                    "eje_y": "Stock actual",
                    "puntos": [
                        {
                            "etiqueta": row["producto__nombre"],
                            "total": row["cantidad_actual"],
                        }
                        for row in resultados
                    ],
                },
            },
            "resultados": resultados,
        }

    @staticmethod
    def _reporte_promociones(filtros: Dict[str, Any]) -> Dict[str, Any]:
        hoy = filtros.get("fecha_referencia") or date.today()
        estado_promocion = filtros.get("estado_promocion", "TODAS").upper()

        qs = Promocion.objects.all()

        if estado_promocion == "ACTIVAS":
            qs = qs.filter(estado="ACTIVA", fecha_inicio__lte=hoy).filter(
                fecha_fin__isnull=True
            ) | qs.filter(estado="ACTIVA", fecha_inicio__lte=hoy, fecha_fin__gte=hoy)
        elif estado_promocion == "EXPIRADAS":
            qs = qs.filter(estado="EXPIRADA")

        if not qs.exists():
            raise NoDataForReport("No existen promociones para los filtros indicados.")

        activas = qs.filter(estado="ACTIVA").count()
        expiradas = qs.filter(estado="EXPIRADA").count()

        resultados = list(
            qs.values(
                "id_promocion",
                "nombre",
                "codigo_descuento",
                "fecha_inicio",
                "fecha_fin",
                "estado",
            ).order_by("fecha_inicio")
        )

        return {
            "tipo_reporte": ReportType.PROMOCIONES,
            "filtros": filtros,
            "resumen": {
                "total_promociones": qs.count(),
                "activas": activas,
                "expiradas": expiradas,
                "serie_grafico": {
                    "tipo": "pastel",
                    "eje_x": "Estado",
                    "eje_y": "Cantidad",
                    "puntos": [
                        {"etiqueta": "ACTIVAS", "total": activas},
                        {"etiqueta": "EXPIRADAS", "total": expiradas},
                    ],
                },
            },
            "resultados": resultados,
        }

    @staticmethod
    def _reporte_bitacora(filtros: Dict[str, Any]) -> Dict[str, Any]:
        qs = Bitacora.objects.select_related("id_usuario")

        qs = ReportesService._aplicar_rango_fechas(qs, "fecha_hora", filtros)

        accion = filtros.get("accion")
        if accion:
            qs = qs.filter(accion=accion)

        usuario_id = filtros.get("usuario_id")
        if usuario_id:
            qs = qs.filter(id_usuario_id=usuario_id)

        if not qs.exists():
            raise NoDataForReport(
                "No existen eventos de bitácora para los filtros indicados."
            )

        total_eventos = qs.count()

        por_accion = (
            qs.values("accion")
            .annotate(total=Count("id_bitacora"))
            .order_by("-total")
        )

        por_usuario = (
            qs.filter(id_usuario__isnull=False)
            .values("id_usuario_id", "id_usuario__nombre_usuario")
            .annotate(total=Count("id_bitacora"))
            .order_by("-total")
        )

        filas = list(
            qs.values(
                "id_bitacora",
                "fecha_hora",
                "accion",
                "descripcion",
                "ip",
                "id_usuario_id",
                "id_usuario__nombre_usuario",
            ).order_by("-fecha_hora")
        )

        resultados = [
            {
                "id_bitacora": row["id_bitacora"],
                "fecha_hora": row["fecha_hora"],
                "accion": row["accion"],
                "descripcion": row["descripcion"],
                "ip": row["ip"],
                "id_usuario": row["id_usuario_id"],
                "nombre_usuario": row["id_usuario__nombre_usuario"],
            }
            for row in filas
        ]

        return {
            "tipo_reporte": ReportType.BITACORA,
            "filtros": filtros,
            "resumen": {
                "total_eventos": total_eventos,
                "por_accion": list(por_accion),
                "por_usuario": list(por_usuario),
                "serie_grafico": {
                    "tipo": "barra",
                    "eje_x": "Acci��n",
                    "eje_y": "Eventos",
                    "puntos": [
                        {"etiqueta": row["accion"], "total": row["total"]}
                        for row in por_accion
                    ],
                },
            },
            "resultados": resultados,
        }
