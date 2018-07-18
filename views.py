# -*- coding: utf-8 -*-
import os
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import formats
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import View
from geonode.layers.models import Layer
from geonode.layers.views import _resolve_layer
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import get_objects_for_user, get_perms

from cartoview.app_manager.helpers import create_direcotry
from cartoview.log_handler import get_logger
from .decorators import time_it
from .exceptions import GpkgLayerException
from .forms import GpkgUploadForm
from .handlers import GpkgManager, get_connection
from .models import GpkgUpload
from .publishers import GeonodePublisher, GeoserverPublisher
from .style_manager import StyleManager
from .utils import SLUGIFIER, get_sld_body

_PERMISSION_MSG_VIEW = ('You don\'t have permissions to view this document')
logger = get_logger(__name__)


@login_required
@permission_required_or_403('gpkg_manager.publish_from_package',
                            (GpkgUpload, 'id', 'upload_id'))
@require_http_methods([
    'GET',
])
@time_it
def get_compatible_layers(request, upload_id, layername):
    layername = str(layername)
    permitted = get_objects_for_user(request.user, 'base.change_resourcebase')
    permitted_layers = Layer.objects.filter(id__in=permitted)
    try:
        obj = GpkgUpload.objects.get(id=upload_id)
        layers = []
        for layer in permitted_layers:
            try:
                check = obj.gpkg_manager.check_schema_geonode(
                    layername, str(layer.alternate))
                lyr = {
                    "name": layer.alternate,
                    "deleted_fields": check.get("deleted_fields"),
                    "new_fields": check.get("new_fields"),
                    "urls": {
                        "reload_url":
                        reverse(
                            'reload_layer',
                            args=(upload_id, layername, layer.alternate))
                    }
                }
                layers.append(lyr)
            except Exception as e:
                logger.error(e.message)

        data = {"status": "success", "layers": layers}
        status = 200
    except (GpkgUpload.DoesNotExist, Layer.DoesNotExist,
            GpkgLayerException), e:
        data = {"status": False, "message": e.message}
        status = 404
    return JsonResponse(data, status=status)


@login_required
@permission_required_or_403('gpkg_manager.publish_from_package',
                            (GpkgUpload, 'id', 'upload_id'))
@require_http_methods([
    'GET',
])
def reload_layer(request, upload_id, layername, glayername):
    layername = str(layername)
    glayername = str(glayername)
    layer = _resolve_layer(request, glayername, 'base.change_resourcebase',
                           _PERMISSION_MSG_VIEW)
    try:
        obj = GpkgUpload.objects.get(id=upload_id)
        gpkg_layer = obj.gpkg_manager.get_layer_by_name(layername)
        if not gpkg_layer:
            raise GpkgLayerException("No Layer with this name in the package")
        if not obj.gpkg_manager.check_schema_geonode(layername,
                                                     str(layer.alternate)):
            raise GpkgLayerException("Invalid schema")
        geonode_manager = GpkgManager(get_connection(), is_postgis=True)
        gpkg_layer.copy_to_source(
            geonode_manager.source,
            overwrite=True,
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
        uploads = get_objects_for_user(user, 'gpkg_manager.view_package')
        permitted = get_objects_for_user(request.user,
                                         'base.download_resourcebase')
        permitted_layers = Layer.objects.filter(id__in=permitted)
        return render(
            request,
            "gpkg_manager/upload.html",
            context={
                'uploads':
                uploads,
                'download_layers': [{
                    "typename": layer.alternate,
                    "title": layer.title
                } for layer in permitted_layers]
            })

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UploadView, self).dispatch(*args, **kwargs)

    def post(self, request):
        form = GpkgUploadForm(request.POST or None, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            data = {
                'is_valid':
                True,
                'name':
                obj.package_name,
                "id":
                obj.id,
                "uploaded_at":
                formats.date_format(obj.uploaded_at, "SHORT_DATETIME_FORMAT"),
                "layers": [{
                    'name': layer.name,
                    'type': layer.geometry_type_name,
                    'feature_count': layer.feature_count,
                    'expected_publish_name': layer.get_new_name(),
                    'urls': {
                        'publish_url':
                        reverse(
                            'geopackage_publish',
                            kwargs={
                                "upload_id": obj.id,
                                "layername": layer.name
                            }),
                        'compatible_layers':
                        reverse(
                            'compatible_layers', args=(obj.id, layer.name))
                    }
                } for layer in obj.gpkg_manager.get_layers()],
                'download_url':
                obj.package.url,
                'delete_url':
                reverse('geopackage_delete', args=(obj.id, )),
            }
        else:
            data = {'is_valid': False}
        return JsonResponse(data)


@login_required
@permission_required_or_403('gpkg_manager.download_package',
                            (GpkgUpload, 'id', 'upload_id'))
@require_http_methods([
    'GET',
])
def deleteUpload(request, upload_id):
    try:
        # TODO:Check if user has permisssion to Delete this package
        obj = GpkgUpload.objects.get(id=upload_id)
        obj.delete()
        data = {"status": "success", "message": "Object has been Deleted"}
        status = 200
    except GpkgUpload.DoesNotExist:
        data = {"status": "failed", "message": "Object Not Found"}
        status = 404
    return JsonResponse(data, status=status)


@login_required
@require_http_methods([
    'GET',
])
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
@permission_required_or_403('gpkg_manager.publish_from_package',
                            (GpkgUpload, 'id', 'upload_id'))
@time_it
def publish_layer(request, upload_id, layername, publish_name=None):
    user = request.user
    layername = str(layername)
    publish_name = str(publish_name)
    gs_layername = SLUGIFIER(layername) if not publish_name else SLUGIFIER(
        publish_name)
    gs_layername = str(gs_layername)
    upload = get_object_or_404(GpkgUpload, pk=upload_id)
    if 'publish_from_package' in get_perms(user, upload):
        manager = upload.gpkg_manager
        package_layer = manager.get_layer_by_name(layername)
        conn = get_connection()
        gs_pub = GeoserverPublisher()
        stm = StyleManager(upload.package.path)
        geonode_pub = GeonodePublisher(owner=request.user)
        tablename = manager.layer_to_postgis(
            layername, conn, overwrite=False, name=gs_layername)
        if not publish_name:
            gs_layername = package_layer.get_new_name()
        gs_pub.publish_postgis_layer(tablename, layername=gs_layername)
        try:
            layer = geonode_pub.publish(gs_layername)
            if layer:
                gpkg_style = stm.get_style(layername)
                if gpkg_style:
                    sld_body = stm.convert_sld_attributes(gpkg_style.styleSLD)
                    name = gpkg_style.styleName
                    # TODO: handle none default styles
                    # useDefault = gpkg_style.useAsDefault
                    style = stm.upload_style(name, sld_body, overwrite=True)
                    stm.set_default_layer_style(layer.alternate, style.name)
                    layer.default_style = style
                    layer.save()
                return JsonResponse({
                    "status":
                    "success",
                    "layer_url":
                    reverse(
                        'layer_detail',
                        kwargs={
                            "layername": layer.alternate,
                        })
                })
        except Exception as e:
            logger.error(e.message)
            if tablename:
                logger.error("DELETING Table {} from source".format(tablename))
                source = manager.open_source(conn, True)
                source.DeleteLayer(tablename)
            if gs_layername and Layer.objects.filter(
                    alternate__icontains=gs_layername).count() == 0:
                gs_pub.delete_layer(gs_layername)

    return JsonResponse(
        {
            'status': 'failed',
            'message': "Layer Publish Failed \
    please Contact portal admin"
        },
        status=500)


def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i + n]


@login_required
@require_http_methods([
    'GET',
])
def download_layers(request):
    today = datetime.now()
    date_as_path = today.strftime("%Y/%m/%d")
    file_suff = today.strftime("%Y_%m_%d-%H_%M_%S")
    file_name = 'download_{}.gpkg'.format(file_suff)
    file_dir = os.path.join("packages_download", date_as_path,
                            request.user.username)
    package_url = os.path.join(file_dir, file_name)
    package_dir = os.path.join(settings.MEDIA_ROOT, file_dir)
    create_direcotry(package_dir)
    if not os.path.isdir(package_dir) or not os.access(package_dir, os.W_OK):
        return HttpResponseForbidden('maybe destination is not writable\
         or not a directory')
    package_path = os.path.join(package_dir, file_name)
    layernames = request.GET.get('layers', None)
    if not layernames:
        return HttpResponseForbidden("No layers provided")
    layernames = [str(layername) for layername in layernames.split(',')]
    permitted = get_objects_for_user(request.user,
                                     'base.download_resourcebase')
    permitted_layers = Layer.objects.filter(id__in=permitted)
    permitted_layers = [
        layer for layer in permitted_layers if layer.alternate in layernames
    ]
    ds = GpkgManager.open_source(get_connection(), is_postgres=True)
    if not ds:
        return HttpResponseForbidden("Cannot connect to database")
    layer_styles = []
    table_names = []
    for layer in permitted_layers:
        typename = str(layer.alternate)
        table_name = typename.split(":").pop()
        if GpkgManager.source_layer_exists(ds, table_name):
            table_names.append(table_name)
            gattr = str(
                layer.attribute_set.filter(
                    attribute_type__contains='gml').first().attribute)
            layer_style = layer.default_style
            sld_url = layer_style.sld_url
            style_name = str(layer_style.name)
            layer_styles.append((table_name, gattr, style_name,
                                 get_sld_body(sld_url)))
    GpkgManager.postgis_as_gpkg(
        get_connection(), package_path, layernames=table_names)
    stm = StyleManager(package_path)
    stm.create_table()
    for style in layer_styles:
        stm.add_style(*style, default=True)
    return redirect(os.path.join(settings.MEDIA_URL, package_url))
