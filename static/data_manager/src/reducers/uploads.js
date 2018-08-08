import {
    ADD_UPLOAD,
    ADD_UPLOADS,
    DELETE_UPLOAD,
    DELETE_UPLOADS,
    SET_TOTAL_COUNT,
    SET_UPLOADS,
    UPLOADS_LOADING
} from '../actions/constants'
export function uploads( state = [], action ) {
    switch ( action.type ) {
    case ADD_UPLOAD:
        return [ action.payload, ...state ]
    case ADD_UPLOADS:
        return [ ...state, ...action.payload ]
    case DELETE_UPLOAD:
        return state.filter( upload => upload.id != action.payload )
    case DELETE_UPLOADS:
        return state.map( upload => !action.payload.includes( upload.id ) )
    case SET_UPLOADS:
        return action.payload
    default:
        return state
    }
}
export function uploadsLoading( state = true, action ) {
    switch ( action.type ) {
    case UPLOADS_LOADING:
        return action.payload
    default:
        return state
    }
}
export function uploadsTotalCount( state = 0, action ) {
    switch ( action.type ) {
    case SET_TOTAL_COUNT:
        return action.payload
    default:
        return state
    }
}
