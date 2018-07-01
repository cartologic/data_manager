from django.shortcuts import render
from .forms import GpkgUploadForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.generic import View
from django.core.urlresolvers import reverse
from django.utils import formats
from .models import GpkgUpload
from guardian.shortcuts import get_objects_for_user
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from .publishers import GeonodePublisher, GeoserverPublisher
from .handlers import (StyleManager, SLUGIFIER,
                       GpkgLayerException, get_connection, GpkgManager)
from cartoview.log_handler import get_logger
from django.views.decorators.http import require_http_methods
from geonode.layers.models import Layer
from geonode.layers.views import _resolve_layer
_PERMISSION_MSG_VIEW = ('You don\'t have permissions to view this document')
logger = get_logger(__name__)


@login_required
@require_http_methods(['GET', ])
def get_compatible_layers(request, upload_id, layername):
    layername = str(layername)
    permitted = get_objects_for_user(
        request.user, 'base.change_resourcebase')
    permitted_layers = Layer.objects.filter(id__in=permitted)
    try:
        obj = GpkgUpload.objects.get(id=upload_id)
        layers = []
        for layer in permitted_layers:
            print obj.gpkg_manager.check_schema_geonode(
                layername, str(layer.alternate))
        layers = [{"name": layer.alternate, "urls": {"reload_url":
                                                     reverse('reload_layer',
                                                             args=(upload_id,
                                                                   layername,
                                                                   layer.alternate)
                                                             )}}
                  for layer in permitted_layers
                  if obj.gpkg_manager.check_schema_geonode(
            layername, str(layer.alternate))]
        data = {"status": "success", "layers": layers}
        status = 200
    except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
            GpkgLayerException), e:
        data = {"status": False, "message": e.message}
        status = 404
    return JsonResponse(data, status=status)


@login_required
@require_http_methods(['GET', ])
def reload_layer(request, upload_id, layername, glayername):
    layername = str(layername)
    glayername = str(glayername)
    layer = _resolve_layer(
        request,
        glayername,
        'base.change_resourcebase',
        _PERMISSION_MSG_VIEW)
    try:
        obj = GpkgUpload.objects.get(id=upload_id)
        gpkg_layer = obj.gpkg_manager.get_layer_by_name(layername)
        if not gpkg_layer:
            raise GpkgLayerException("No Layer with this name in the package")
        if not obj.gpkg_manager.check_schema_geonode(
                layername, str(layer.alternate)):
            raise GpkgLayerException("Invalid schema")
        geonode_manager = GpkgManager(get_connection(), is_postgis=True)
        gpkg_layer.copy_to_source(
            geonode_manager.source, overwrite=True,
            name=glayername.split(":").pop())
        data = {"status": "success", "message": "Layer reloaded succesfully"}
        status = 200
    except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
            GpkgLayerException), e:
        data = {"status": "failed", "message": e.message}
        status = 404
    return JsonResponse(data, status=status)


class UploadView(View):
    def get(self, request):
        user = request.user
        uploads = GpkgUpload.objects.filter(user=user)
        return render(request, "gpkg_manager/upload.html",
                      context={'uploads': uploads})

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UploadView, self).dispatch(*args, **kwargs)

    def post(self, request):
        form = GpkgUploadForm(request.POST or None, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            data = {'is_valid': True, 'name': obj.package_name,
                    "id": obj.id,
                    "uploaded_at": formats.date_format(obj.uploaded_at,
                                                       "SHORT_DATETIME_FORMAT"),
                    "layers": [{'name': layer.name,
                                'urls': {'publish_url':
                                         reverse('geopackage_publish',
                                                 kwargs={"upload_id": obj.id,
                                                         "layername":
                                                         layer.name})}}
                               for layer in obj.gpkg_manager.get_layers()],
                    'url':  obj.package.url}
        else:
            data = {'is_valid': False}
        return JsonResponse(data)

@login_required
@require_http_methods(['GET', ])
def compare_to_geonode_layer(request, upload_id, layername, glayername):
    layername = str(layername)
    glayername = str(glayername)
    try:
        obj = GpkgUpload.objects.get(id=upload_id)
        check = obj.gpkg_manager.check_schema_geonode(layername, glayername)
        data = {"status": "success", "compitable": check}
        status = 200
    except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
            GpkgLayerException), e:
        data = {"status": "failed", "message": e.message}
        status = 404
    return JsonResponse(data, status=status)

# NOTE: this view will publish a new layer each time


@login_required
def publish_layer(request, upload_id, layername):
    user = request.user
    layername = str(layername)
    gs_layername = SLUGIFIER(layername)
    upload = get_object_or_404(GpkgUpload, pk=upload_id)
    if user == upload.user or user.is_superuser:
        manager = upload.gpkg_manager
        package_layer = manager.get_layer_by_name(layername)
        conn = get_connection()
        gs_pub = GeoserverPublisher()
        stm = StyleManager(upload.package.path)
        geonode_pub = GeonodePublisher()
        tablename = manager.layer_to_postgis(layername, conn, overwrite=False)
        if package_layer.check_geonode_layer(gs_layername):
            gs_layername = package_layer.get_new_name()
        gs_pub.publish_postgis_layer(
            tablename, layername=gs_layername)
        try:
            layer = geonode_pub.publish(gs_layername)
            if layer:
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
                return JsonResponse({"status": "success", "layer_url": reverse(
                    'layer_detail', kwargs={"layername": layer.alternate, })})
        except Exception as e:
            logger.error(e.message)
            logger.error("DELETING Table {} from source".format(tablename))
            source = manager.open_source(conn, True)
            source.DeleteLayer(tablename)

    return JsonResponse({'status': 'failed', 'message': "Layer Publish Failed \
    please Contact portal admin"}, status=500)
