import { ApiRequests } from '../utils/utils'
import { LIMIT } from '../constants'
export default class GeopackageApi {
    constructor( username, token, urls ) {
        this.requests = new ApiRequests( username, token )
        this.urls = urls
    }
    getUploads( offset = 0, pageLimit = LIMIT ) {
        return this.requests.doGet(
            `${this.urls.uploadsURL}?offset=${offset}&limit=${pageLimit}`
        )
    }
    getPermissions() {
        return this.requests.doGet( this.urls.permissionsURL )
    }
}
