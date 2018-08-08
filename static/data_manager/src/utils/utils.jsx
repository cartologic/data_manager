function updateProgress(evt) {
    if (evt.lengthComputable) {
        let percentComplete = (evt.loaded / evt.total) * 100
        console.log("Progress is ----> " + percentComplete)
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
    doPost(url, data, extraHeaders = {}) {
        return fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: new Headers({
                'Authorization': `ApiKey ${this.username}:${this.token}`,
                ...extraHeaders
            }),
            body: data
        }).then((response) => response.json())
    }
    doDelete(url, extraHeaders = {}) {
        return fetch(url, {
            method: 'DELETE',
            credentials: 'include',
            headers: {
                'Authorization': `ApiKey ${this.username}:${this.token}`,
                ...extraHeaders
            }
        }).then((response) => response.text())
    }
    doGet(url, extraHeaders = {}) {
        return fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Authorization': `ApiKey ${this.username}:${this.token}`,
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
        xhr.setRequestHeader('Authorization', `ApiKey ${this.username}:${this.token}`)
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