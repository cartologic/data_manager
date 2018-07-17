import React, { Component } from 'react'

import { ADD_PERMISSION_OP } from '../actions/constants'
import { ApiRequests } from '../utils/utils'
import Avatar from '@material-ui/core/Avatar'
import FileIcon from '@material-ui/icons/FileUpload'
import ListItem from '@material-ui/core/ListItem'
import ListItemText from '@material-ui/core/ListItemText'
import PropTypes from 'prop-types'
import { addUpload } from '../actions/uploads'
import { connect } from 'react-redux'
import { updatePermissions } from '../actions/permissions'
import { withStyles } from '@material-ui/core/styles'

const styles = theme => ({
})
class UploadItem extends Component {
    constructor(props) {
        super(props)
        const { username, token } = this.props
        this.state = { progress: 0, error: null }
        let newToken = token.split(" for ")[0]
        this.requests = new ApiRequests(username, newToken)
    }
    componentDidMount() {
        const { urls, file, addUpload, updatePermissions, permissions, removeUploadedFile } = this.props
        let formData = new FormData()
        formData.append("package", file)
        this.requests.uploadWithProgress(urls.uploadsURL, formData, (result) => {
            // result = JSON.parse(result)
            // console.log(result)
        }, (evt) => {
            if (evt.lengthComputable) {
                let percentComplete = (evt.loaded / evt.total) * 100
                this.setState({ progress: percentComplete })
            }
        }, (xhr) => {
            if (xhr.status === 201) {
                setTimeout(function () {
                    const newUpload = JSON.parse(xhr.responseText)
                    addUpload(newUpload)
                    updatePermissions(Object.keys(permissions), newUpload.id, ADD_PERMISSION_OP)
                    removeUploadedFile(file)
                }, 1000)
            }
        }, (xhr) => {
            if (xhr.status >= 400) {
                this.setState({ error: xhr.statusText })
            }
        })
    }
    render() {
        const { progress, error } = this.state
        const { file } = this.props
        return (
            <ListItem>
                <Avatar>
                    <FileIcon />
                </Avatar>
                <ListItemText primary={file.name} secondary={!error ? `${progress}% Complete` : error} />
            </ListItem>
        )
    }
}
UploadItem.propTypes = {
    file: PropTypes.object.isRequired,
    urls: PropTypes.object.isRequired,
    username: PropTypes.string.isRequired,
    token: PropTypes.string.isRequired,
    addUpload: PropTypes.func.isRequired,
    updatePermissions: PropTypes.func.isRequired,
    permissions: PropTypes.object.isRequired,
    removeUploadedFile: PropTypes.func.isRequired,
}
const mapStateToProps = (state) => {
    return {
        username: state.username,
        token: state.token,
        urls: state.urls,
        permissions: state.permissions,
    }
}
const mapDispatchToProps = (dispatch) => {
    return {
        addUpload: (upload) => dispatch(addUpload(upload)),
        updatePermissions: (keys, id, operation) => dispatch(updatePermissions(keys, id, operation)),
    }
}
let App = connect(mapStateToProps, mapDispatchToProps)(withStyles(styles)(UploadItem))
export default App