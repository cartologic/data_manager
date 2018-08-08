import { ApiRequests, convertToSlug } from '../utils/utils'

import Divider from '@material-ui/core/Divider'
import Paper from '@material-ui/core/Paper'
import PropTypes from 'prop-types'
import PublishModal from './PublishModal'
import React from 'react'
import Typography from '@material-ui/core/Typography'
import UpdateExistingModal from './UpdateExistingModal'
import UploadListItem from './UploadListItem'
import { connect } from 'react-redux'
import { withStyles } from '@material-ui/core/styles'

const styles = theme => ({
    root: {
        width: '100%',
        marginTop: theme.spacing.unit * 2,
        marginBottom: theme.spacing.unit * 2,
        boxSizing: 'border-box',
        padding: theme.spacing.unit,
    },
    textCenter: {
        textAlign: 'center'
    },
    title: {
        margin: theme.spacing.unit,
        textAlign: 'center'
    },
    button: {
        margin: theme.spacing.unit,
    },
    flexGrow: {
        flexGrow: 1
    },
    panelSummary: {
        display: 'flex',
        alignItems: 'center'
    },
    table: {
        width: "100%"
    },
    tableWrapper: {
        overflowX: 'auto',
        width: "100%"
    },
    row: {
        '&:nth-of-type(odd)': {
            backgroundColor: theme.palette.background.default,
        },
    },
    progress: {
        margin: theme.spacing.unit * 2,
    },
})

class UploadsList extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            publishModalOpen: false,
            publishName: null,
            currentLayer: null,
            publishLoading: false,
            publishError: null,
            updateError: null,
            updateExistingLoading: false,
            updateExistingModalOpen: false,
        }
        const { token, username } = this.props
        let newToken = token.split(" for ")[0]
        this.requests = new ApiRequests(username, newToken)
    }
    setCurrentLayerOpenPublishModal = (layer) => {
        this.setState({ currentLayer: layer, publishName: layer.expected_name }, this.handlPublishModal)
    }
    setCurrentLayerOpenUpdateModal = (layer) => {
        this.setState({ currentLayer: layer }, this.handleUpdateExistingModal)
    }
    handlPublishModal = () => {
        const { publishModalOpen } = this.state
        this.setState({ publishModalOpen: !publishModalOpen, publishError: null })
    }
    handleUpdateExistingModal = () => {
        const { updateExistingModalOpen } = this.state
        this.setState({ updateExistingModalOpen: !updateExistingModalOpen, updateError: null })
    }
    handlePublishName = (event) => {
        this.setState({ publishName: convertToSlug(event.target.value) })
    }
    replaceLayer = () => {

    }
    publishLayer = () => {
        const { currentLayer, publishName } = this.state
        this.setState({ publishLoading: true }, () => {
            this.requests.doGet(`${currentLayer.urls.publish_url}?publish_name=${publishName}`).then(result => {
                if (result.layer_url) {
                    window.location.href = result.layer_url
                } else {
                    throw Error(result.error_message)
                }
            }).catch(error => {
                this.setState({ publishLoading: false, publishError: error.message })
            })
        })


    }
    render() {
        const { classes, uploads } = this.props
        const { publishModalOpen, publishLoading, publishError, publishName, updateExistingLoading, updateError, updateExistingModalOpen, currentLayer } = this.state
        return (
            <div className={classes.root}>
                <PublishModal handlePublishName={this.handlePublishName} publishLoading={publishLoading} publishError={publishError} publishName={publishName} handlPublishModal={this.handlPublishModal} publishLayer={this.publishLayer} publishModalOpen={publishModalOpen} />
                <UpdateExistingModal currentLayer={currentLayer} updateExistingLoading={updateExistingLoading} updateError={updateError} handleUpdateExistingModal={this.handleUpdateExistingModal} replaceLayer={this.replaceLayer} updateExistingModalOpen={updateExistingModalOpen} />
                <Divider />
                <Typography noWrap color={"default"} className={classes.title} variant="headline">{"Uploaded List"}</Typography>
                {uploads && uploads.map((upload, index) => {
                    return <UploadListItem setCurrentLayerOpenUpdateModal={this.setCurrentLayerOpenUpdateModal} upload={upload} setCurrentLayerOpenPublishModal={this.setCurrentLayerOpenPublishModal} key={index} />
                })}
            </div>
        )
    }
}

UploadsList.propTypes = {
    classes: PropTypes.object.isRequired,
    uploads: PropTypes.array.isRequired,
    token: PropTypes.string.isRequired,
    urls: PropTypes.object.isRequired,
    username: PropTypes.string.isRequired,
}
const mapStateToProps = (state) => {
    return {
        username: state.username,
        token: state.token,
        urls: state.urls,
        uploads: state.uploads,
    }
}
const mapDispatchToProps = (dispatch) => {
    return {
    }
}
export default connect(mapStateToProps, mapDispatchToProps)(withStyles(styles)(UploadsList))
// return <li key={index} className="list-group-item ">
//     <div className="layer-item flex-element flex-space-between equal-area text-center flex-center">
//         <span className="text-wrap equal-area text-left">{`Layer Name: ${layer.name}`}</span>
//         <span className="equal-area">Type:{layer.geometry_type_name}</span>
//         <span className="equal-area">Feature Count:{layer.feature_count}</span>
//         {checkPermission(permissions, 'publish_from_package', upload.id) && <button className="btn btn-primary glayer-actions" onClick={() => this.setLayerOpenModal(layer)}>Publish New</button>}
//         {checkPermission(permissions, 'publish_from_package', upload.id) && <button className="btn btn-primary glayer-actions" onclick="getCompatibleLayres('{% url 'compatible_layers' upload_id=upload.id layername=layer.name %}')">Update</button>}
//     </div>

// </li>