import {
    ADD_PERMISSION_OP,
    DELETE_PERMISSION_OP,
    PERMISSIONS_LOADING,
    SET_PERMISSIONS,
    UPDATE_PERMISSIONS
} from '../actions/constants'

function updateCurrentPermissions( permissions, updateObj ) {
    let parialUpdated = {}
    updateObj.keys.map( key => {
        let perm = permissions[ key ]
        let newIds = []
        switch ( updateObj.operation ) {
        case DELETE_PERMISSION_OP:
            newIds = perm.ids.filter( id => id != updateObj.id )
            break
        case ADD_PERMISSION_OP:
            newIds = [ ...perm.ids, updateObj.id ]
            break
        default:
            throw Error( "Invalid Operation on Permission Obj" )
        }
        perm = { ...perm,
            ids: newIds
        }
        parialUpdated[ key ] = perm
    } )
    return { ...permissions, ...parialUpdated }
}
export function permissions( state = [], action ) {
    switch ( action.type ) {
    case SET_PERMISSIONS:
        return action.payload
    case UPDATE_PERMISSIONS:
        return { ...state, ...updateCurrentPermissions( state, action.payload ) }
    default:
        return state
    }
}
export function permissionsLoading( state = true, action ) {
    switch ( action.type ) {
    case PERMISSIONS_LOADING:
        return action.payload
    default:
        return state
    }
}
