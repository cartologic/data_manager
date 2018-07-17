import {
    PERMISSIONS_LOADING,
    SET_PERMISSIONS,
    UPDATE_PERMISSIONS
} from './constants'
export function permissions( permissions ) {
    return {
        type: SET_PERMISSIONS,
        payload: permissions
    }
}
export function updatePermissions( permissionKeys, id, operation ) {
    return {
        type: UPDATE_PERMISSIONS,
        payload: {
            keys: permissionKeys,
            id,
            operation,
        }
    }
}
export function permissionsLoading( loading ) {
    return {
        type: PERMISSIONS_LOADING,
        payload: loading
    }
}
