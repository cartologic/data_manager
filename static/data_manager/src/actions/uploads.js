import {
    ADD_UPLOAD,
    ADD_UPLOADS,
    DELETE_UPLOAD,
    DELETE_UPLOADS,
    SET_TOTAL_COUNT,
    SET_UPLOADS,
    UPLOADS_LOADING
} from './constants'
export function addUpload( upload ) {
    return {
        type: ADD_UPLOAD,
        payload: upload
    }
}
export function addUploads( uploads ) {
    return {
        type: ADD_UPLOADS,
        payload: uploads
    }
}
export function deleteUpload( uploadID ) {
    return {
        type: DELETE_UPLOAD,
        payload: uploadID
    }
}
export function deleteUploads( ids ) {
    return {
        type: DELETE_UPLOADS,
        payload: ids
    }
}
export function newUploads( uploads ) {
    return {
        type: SET_UPLOADS,
        payload: uploads
    }
}
export function uploadsLoading( loading ) {
    return {
        type: UPLOADS_LOADING,
        payload: loading
    }
}
export function uploadsTotalCount( count ) {
    return {
        type: SET_TOTAL_COUNT,
        payload: count
    }
}
