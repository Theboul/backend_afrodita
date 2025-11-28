from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Promocion',
            fields=[
                ('id_promocion', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=50)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('codigo_descuento', models.CharField(max_length=20, unique=True)),
                ('tipo', models.CharField(choices=[('DESCUENTO_PORCENTAJE', 'Descuento porcentaje'), ('DESCUENTO_MONTO', 'Descuento monto'), ('COMBO', 'Combo'), ('DOS_X_UNO', '2x1')], default='DESCUENTO_PORCENTAJE', max_length=20)),
                ('valor_descuento', models.DecimalField(blank=True, decimal_places=2, help_text='Porcentaje o monto según el tipo de promoción', max_digits=6, null=True)),
                ('fecha_inicio', models.DateField(blank=True, null=True)),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('ACTIVA', 'Activa'), ('INACTIVA', 'Inactiva')], default='ACTIVA', max_length=15)),
            ],
            options={
                'db_table': 'promocion',
                'ordering': ['-fecha_inicio', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='PromocionProducto',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('producto', models.ForeignKey(db_column='id_producto', on_delete=django.db.models.deletion.CASCADE, related_name='productos_promocion', to='productos.producto')),
                ('promocion', models.ForeignKey(db_column='id_promocion', on_delete=django.db.models.deletion.CASCADE, related_name='promociones_productos', to='promocion.promocion')),
            ],
            options={
                'db_table': 'promocion_producto',
                'unique_together': {('promocion', 'producto')},
            },
        ),
        migrations.AddField(
            model_name='promocion',
            name='productos',
            field=models.ManyToManyField(blank=True, related_name='promociones', through='promocion.PromocionProducto', to='productos.producto'),
        ),
    ]
