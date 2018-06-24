from django.shortcuts import render, redirect
from .forms import GpkgUploadForm
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import GpkgUpload
from django.shortcuts import get_object_or_404
from .publishers import GeonodePublisher, GeoserverPublisher
from .handlers import GpkgManager
from .utils import get_connection


@login_required
def upload(request):
    form = GpkgUploadForm()
    if request.method == "POST":
        form = GpkgUploadForm(request.POST or None, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            # TODO:redirect to list of user uploads
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
        if not layer.is_geonode_layer:
            if not pg_source.GetLayerByName(layername):
                manager.layer_to_postgis_cmd(layername, conn)
                gs_pub = GeoserverPublisher()
                gs_pub.publish_postgis_layer(layername)
            geonode_pub = GeonodePublisher()
            layer = geonode_pub.publish(layername)
            if layer:
                return redirect('geonode.layers.views.layer_detail',
                                layer.alternate)

    return HttpResponseForbidden()
