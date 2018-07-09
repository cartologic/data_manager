from tastypie.authorization import Authorization
from guardian.shortcuts import get_objects_for_user


class GpkgAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        permitted_ids = get_objects_for_user(
            bundle.request.user, 'gpkg_manager.view_package').values('id')
        return object_list.filter(id__in=permitted_ids)

    def read_detail(self, object_list, bundle):
        if 'schema' in bundle.request.path:
            return True
        return bundle.request.user.has_perm('view_package', bundle.obj)

    def create_list(self, object_list, bundle):
        return object_list

    def create_detail(self, object_list, bundle):
        return (bundle.obj.user == bundle.request.user
                and not bundle.request.user.is_anonymous())

    def update_list(self, object_list, bundle):
        allowed = []
        # Since they may not all be saved, iterate over them.
        for obj in object_list:
            if obj.user == bundle.request.user:
                allowed.append(obj)

        return allowed

    def update_detail(self, object_list, bundle):
        return bundle.obj.user == bundle.request.user

    def delete_list(self, object_list, bundle):
        permitted_ids = get_objects_for_user(
            bundle.request.user, 'gpkg_manager.delete_package').values('id')
        return object_list.filter(id__in=permitted_ids)

    def delete_detail(self, object_list, bundle):
        return bundle.request.user.has_perm('delete_package', bundle.obj)
