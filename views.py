from django.shortcuts import render, redirect
from .forms import GpkgUploadForm
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import GpkgUpload
from django.shortcuts import get_object_or_404
from .publishers import GeonodePublisher, GeoserverPublisher
from .handlers import GpkgManager, StyleManager
from .utils import (get_connection, DEFAULT_WORKSPACE,
                    get_gs_store, gs_catalog)


@login_required
def upload(request):
    form = GpkgUploadForm()
    if request.method == "POST":
        form = GpkgUploadForm(request.POST or None, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect('gpkg_manager.views.list_uploads')
    return render(request, "gpkg_manager/upload.html", context={'form': form})


@login_required
def list_uploads(request):
    user = request.user
    uploads = GpkgUpload.objects.filter(user=user)
    return render(request, "gpkg_manager/list.html",
                  context={'uploads': uploads})


@login_required
def publish_layer(request, upload_id, layername):
    user = request.user
    layername = str(layername)
    upload = get_object_or_404(GpkgUpload, pk=upload_id)
    if user == upload.user or user.is_superuser:
        manager = upload.gpkg_manager
        layer = manager.get_layer_by_name(layername)
        conn = get_connection()
        pg_source = GpkgManager.open_source(conn, is_postgres=True)
        gs_pub = GeoserverPublisher()
        stm = StyleManager(upload.package.path)
        geonode_pub = GeonodePublisher()
        expected_name = DEFAULT_WORKSPACE+":"+layername
        if not layer.is_geonode_layer:
            # check if layer not in postgres then add it and publish
            if not pg_source.GetLayerByName(layername):
                manager.layer_to_postgis_cmd(layername, conn)
                gs_pub.publish_postgis_layer(layername)
            # check if layer not in geoserver
            elif not gs_catalog.get_resource(expected_name,
                                             store=get_gs_store(),
                                             workspace=DEFAULT_WORKSPACE):
                gs_pub.publish_postgis_layer(layername)
            layer = geonode_pub.publish(layername)
            gpkg_style = stm.get_style(layername)
            if gpkg_style:
                sld_body = gpkg_style.styleSLD
                name = gpkg_style.styleName
                # TODO: handle none default styles
                # useDefault = gpkg_style.useAsDefault
                style = stm.upload_style(name, sld_body, overwrite=True)
                stm.set_default_layer_style(layer.alternate, style.name)
                layer.default_style = style
                layer.save()

            if layer:
                return redirect('geonode.layers.views.layer_detail',
                                layer.alternate)

    return HttpResponseForbidden()
