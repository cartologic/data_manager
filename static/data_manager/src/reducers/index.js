import {
    permissions,
    permissionsLoading
} from './permissions'
import {
    token,
    urls,
    username
} from './other'
import {
    uploads,
    uploadsLoading,
    uploadsTotalCount
} from './uploads'

import { combineReducers } from 'redux'
export default combineReducers( {
    uploads,
    uploadsLoading,
    permissions,
    permissionsLoading,
    uploadsTotalCount,
    urls,
    username,
    authToken: token,
} )
