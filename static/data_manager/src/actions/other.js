import {
    SET_TOKEN,
    SET_URLS,
    SET_USERNAME
} from './constants'
export function setURLS( urls ) {
    return {
        type: SET_URLS,
        payload: urls
    }
}
export function setUsername( username ) {
    return {
        type: SET_USERNAME,
        payload: username
    }
}
export function setToken( token ) {
    return {
        type: SET_TOKEN,
        payload: token
    }
}
