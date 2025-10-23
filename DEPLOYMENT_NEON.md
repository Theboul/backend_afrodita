# 🐘 Guía Rápida: Desplegar en Render con Neon Database

## ✅ **Ventajas de Usar Neon con Render**

- ✅ Base de datos **permanente** (no expira como Render PostgreSQL gratis)
- ✅ Mejor rendimiento y almacenamiento (0.5GB gratis vs 256MB de Render)
- ✅ Backups automáticos
- ✅ No necesitas crear PostgreSQL en Render
- ✅ Más flexible - puedes cambiar de hosting sin migrar BD

---

## 📋 **Pasos Simplificados**

### 1️⃣ Obtener Connection String de Neon

1. Ve a tu proyecto en [Neon Console](https://console.neon.tech)
2. En el dashboard, busca **"Connection String"** o **"Connection Details"**
3. Copia la connection string completa:
   ```
   postgresql://usuario:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

**💡 Tip:** Asegúrate de que incluya `?sslmode=require` al final

---

### 2️⃣ Preparar Proyecto Localmente

```bash
# 1. Generar claves secretas
python generate_secrets.py

# 2. Preparar archivos
.\prepare_deploy.bat

# 3. Commit y push
git add .
git commit -m "Preparar para despliegue en Render con Neon"
git push origin main
```

---

### 3️⃣ Crear Web Service en Render

1. Ve a [Render Dashboard](https://dashboard.render.com)
2. Clic en **"New +"** → **"Web Service"**
3. Conecta tu repositorio GitHub
4. Configura:
   - **Name**: `afrodita-backend`
   - **Region**: Elige cercana a tu región de Neon (ej: Ohio si Neon está en us-east-2)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn afrodita.wsgi:application`
   - **Plan**: Free

---

### 4️⃣ Configurar Variables de Entorno en Render

En la sección **"Environment Variables"** del Web Service:

| Variable | Valor | Dónde obtenerlo |
|----------|-------|-----------------|
| `SECRET_KEY` | `<genera-con-script>` | `python generate_secrets.py` |
| `JWT_SECRET_KEY` | `<genera-con-script>` | `python generate_secrets.py` |
| `DEBUG` | `False` | Escribir manualmente |
| `ALLOWED_HOSTS` | `tu-app.onrender.com` | URL que Render te asigne |
| `DATABASE_URL` | `postgresql://...` | **Copiar desde Neon** ⬅️ |
| `CLOUDINARY_NAME` | `<tu-cloud-name>` | Dashboard de Cloudinary |
| `CLOUDINARY_API_KEY` | `<tu-api-key>` | Dashboard de Cloudinary |
| `CLOUDINARY_API_SECRET` | `<tu-api-secret>` | Dashboard de Cloudinary |
| `CLOUDINARY_SECURE` | `True` | Escribir manualmente |

**🚨 IMPORTANTE:** Para `DATABASE_URL`, usa la connection string completa de Neon.

---

### 5️⃣ Verificar Conexión Neon (Antes de Desplegar)

Verifica que Neon permita conexiones externas:

1. En Neon Console, ve a tu proyecto
2. Settings → IP Allow List
3. Si está habilitado, agrega `0.0.0.0/0` (permitir todas las IPs)
   - O espera a que Render te dé las IPs salientes y agrégalas específicamente

**💡 Por defecto**, Neon permite conexiones desde cualquier IP.

---

### 6️⃣ Desplegar

1. Haz clic en **"Create Web Service"**
2. Render comenzará a construir (5-10 minutos)
3. Monitorea los logs en tiempo real

---

### 7️⃣ Actualizar ALLOWED_HOSTS

Una vez desplegado, Render te asignará una URL (ej: `afrodita-backend.onrender.com`):

1. Ve a **Environment Variables**
2. Edita `ALLOWED_HOSTS`:
   ```
   afrodita-backend.onrender.com
   ```
3. Guarda (Render redesplegará automáticamente)

---

## 🧪 **Verificación Post-Despliegue**

### 1. Verificar API
```
https://tu-app.onrender.com/
```

### 2. Verificar Admin
```
https://tu-app.onrender.com/admin/
```

### 3. Verificar Documentación
```
https://tu-app.onrender.com/api/schema/swagger-ui/
```

### 4. Crear Superusuario
En el **Shell** de Render:
```bash
python manage.py createsuperuser
```

---

## 🔍 **Verificar Conexión a Neon**

Puedes verificar la conexión ejecutando en el Shell de Render:

```bash
python manage.py dbshell
```

O ejecutar:
```bash
python manage.py migrate --check
```

---

## 🚨 **Solución de Problemas**

### Error: "could not connect to server"
- Verifica que `DATABASE_URL` esté correctamente copiado desde Neon
- Asegúrate de incluir `?sslmode=require` al final
- Verifica que tu proyecto Neon no esté suspendido

### Error: "password authentication failed"
- Vuelve a copiar la connection string desde Neon
- Puede que la contraseña contenga caracteres especiales - asegúrate de copiarla completa

### Error: "SSL connection required"
- Agrega `?sslmode=require` al final de `DATABASE_URL`

### La app funciona pero no guarda datos
- Verifica que las migraciones se hayan ejecutado correctamente
- Revisa los logs: `python manage.py showmigrations`

---

## 📊 **Comparación: Neon vs Render PostgreSQL**

| Característica | Neon (Gratis) | Render PostgreSQL (Gratis) |
|----------------|---------------|----------------------------|
| **Duración** | ✅ Permanente | ⚠️ 90 días |
| **Almacenamiento** | ✅ 0.5 GB | ⚠️ 0.256 GB |
| **Backups** | ✅ Automáticos | ⚠️ No incluidos |
| **Suspensión** | Después de 5 min inactividad | N/A |
| **Branching** | ✅ Incluido | ❌ No disponible |
| **Recomendación** | ✅ **MEJOR OPCIÓN** | Solo si necesitas todo en Render |

---

## ✅ **Checklist Rápido**

- [ ] Obtener connection string de Neon (con `?sslmode=require`)
- [ ] Generar claves secretas (`python generate_secrets.py`)
- [ ] Crear cuenta en Cloudinary y obtener credenciales
- [ ] Preparar proyecto (`.\prepare_deploy.bat`)
- [ ] Push a GitHub
- [ ] Crear Web Service en Render (NO crear PostgreSQL)
- [ ] Configurar todas las variables de entorno
- [ ] Desplegar y monitorear logs
- [ ] Actualizar `ALLOWED_HOSTS` con URL de Render
- [ ] Crear superusuario
- [ ] Probar endpoints

---

## 🎉 **¡Listo!**

Tu backend estará funcionando con:
- 🚀 Render (hosting de la aplicación)
- 🐘 Neon (base de datos PostgreSQL)
- ☁️ Cloudinary (almacenamiento de imágenes)

**Tiempo estimado total:** 10-15 minutos

---

## 📚 **Recursos Útiles**

- [Neon Documentation](https://neon.tech/docs)
- [Render Django Guide](https://render.com/docs/deploy-django)
- [Django Production Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
