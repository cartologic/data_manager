function updateProgress(evt) {
    if (evt.lengthComputable) {
        let percentComplete = (evt.loaded / evt.total) * 100
    }
}

function transferComplete(evt) {
    console.log("The transfer is complete.")
}

function transferFailed(evt) {
    console.error("An error occurred while transferring the file.")
}
export function convertToSlug(Text) {
    return Text
        .toLowerCase()
        .replace(/ /g, '_')
        .replace(/[^\w-]+/g, '');
}
export class ApiRequests {
    constructor(username, token) {
        this.token = token
        this.username = username
    }
    getBaseHeaders() {
        let headers = {}
        if (this.token.type === "oauth") {
            headers = {
                ...headers,
                'Authorization': `${this.token.prefix} ${this.token.token}`,
            }
        } else if (this.token.type === "tastypie") {
            headers = {
                ...headers,
                'Authorization': `ApiKey ${this.username}:${this.token.token}`,
            }
        }
        return headers
    }
    doPost(url, data, extraHeaders = {}) {
        return fetch(url, {
            method: 'POST',
            redirect: 'follow',
            credentials: 'include',
            headers: new Headers({
                ...this.getBaseHeaders(),
                ...extraHeaders
            }),
            body: data
        }).then((response) => response.json())
    }
    doDelete(url, extraHeaders = {}) {
        return fetch(url, {
            method: 'DELETE',
            redirect: 'follow',
            credentials: 'include',
            headers: {
                ...this.getBaseHeaders(),
                ...extraHeaders
            }
        }).then((response) => response.text())
    }
    doGet(url, extraHeaders = {}) {
        return fetch(url, {
            method: 'GET',
            redirect: 'follow',
            credentials: 'include',
            headers: {
                ...this.getBaseHeaders(),
                ...extraHeaders
            }
        }).then((response) => response.json())
    }
    uploadWithProgress(url, data, resultFunc, progressFunc = updateProgress, loadFunc = transferComplete, errorFunc = transferFailed, ) {

        let xhr = new XMLHttpRequest()
        xhr.upload.addEventListener("progress", function (evt) {
            progressFunc(evt)
        }, false)
        xhr.addEventListener("load", function (evt) {
            loadFunc(xhr)
        })
        xhr.addEventListener("error", function () {
            errorFunc(xhr)
        })
        xhr.onreadystatechange = function () {
            if (xhr.readyState == XMLHttpRequest.DONE) {
                resultFunc(xhr.responseText)
            }
        }
        xhr.open('POST', url, true)
        xhr.setRequestHeader("Cache-Control", "no-cache")
        let headers = this.getBaseHeaders()
        let headerKeys = Object.keys(headers)
        for (let index = 0; index < headerKeys.length; index++) {
            const headerKey = headerKeys[index];
            const headerValue = headers[headerKey];
            xhr.setRequestHeader(headerKey, headerValue)
        }

        xhr.send(data)

    }
}
export function checkPermission(permissions, permissionKey, id) {
    const permissionIds = permissions[permissionKey].ids
    if (permissionIds.indexOf(id) > -1) {
        return true
    }
    return false
}