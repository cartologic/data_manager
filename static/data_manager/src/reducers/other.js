import {
    SET_TOKEN,
    SET_URLS,
    SET_USERNAME
} from '../actions/constants'
export function username( state = null, action ) {
    switch ( action.type ) {
    case SET_USERNAME:
        return action.payload
    default:
        return state
    }
}
export function urls( state = {}, action ) {
    switch ( action.type ) {
    case SET_URLS:
        return action.payload
    default:
        return state
    }
}
export function token( state = null, action ) {
    switch ( action.type ) {
    case SET_TOKEN:
        return action.payload
    default:
        return state
    }
}
