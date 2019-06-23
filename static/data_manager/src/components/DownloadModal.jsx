import 'react-select/dist/react-select.css'

import { ApiRequests } from '../utils/utils'
import AppBar from '@material-ui/core/AppBar';
import Button from '@material-ui/core/Button'
import CircularProgress from '@material-ui/core/CircularProgress'
import CloseIcon from '@material-ui/icons/Close';
import Dialog from '@material-ui/core/Dialog'
import DialogActions from '@material-ui/core/DialogActions'
import DialogContent from '@material-ui/core/DialogContent'
import DialogContentText from '@material-ui/core/DialogContentText'
import DialogTitle from '@material-ui/core/DialogTitle'
import IconButton from '@material-ui/core/IconButton';
import PropTypes from 'prop-types'
import React from 'react'
import Select from 'react-select'
import Toolbar from '@material-ui/core/Toolbar';
import Typography from '@material-ui/core/Typography'
import classNames from 'classnames'
import { connect } from 'react-redux'
import { withStyles } from '@material-ui/core/styles'

const styles = theme => ({
    flexGrow: {
        flexGrow: 1
    },
    button: {
        margin: theme.spacing.unit
    },
    margin: {
        margin: theme.spacing.unit,
    },
    textField: {
        flexBasis: 200,
    },
    progress: {
        margin: theme.spacing.unit * 2,
    },
    fullWidth: {
        width: '100%'
    },
    layerItem: {
        margin: theme.spacing.unit * 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
    }, dialogTitle: {
        backgroundColor: theme.palette.primary[500],
        marginBottom: theme.spacing.unit * 2
    }, whiteText: {
        color: theme.palette.common.white,
    }
})
class DownloadModal extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            downlaodLayers: [],
            downloadError: null,
            downloadLoading: false
        }
        const { authToken, username } = this.props
        this.requests = new ApiRequests(username, authToken)
    }
    downloadSelectedLayers = () => {
        const { urls } = this.props
        const { downlaodLayers } = this.state
        const layers = downlaodLayers.map(layer => layer.typename.split(":").pop())
        const url = `${urls.downloadURL}?layer_names=${layers.join(',')}`
        this.setState({ downloadModalOpen: false }, () => {
            this.setState({ progressModalOpen: true }, () => {
                this.requests.doGet(url).then(result => {
                    if (result.download_url) {
                        this.setState({ downloadLoading: false, downlaodLayers: [] }, () => { window.location.href = result.download_url })
                    } else {
                        this.setState({ downloadLoading: false, downlaodLayers: [], downloadError: result.error_message })
                    }
                }).catch(error => {
                    this.setState({ downloadLoading: false, downloadError: error.message })
                })
            })
        })
    }
    handleSelectChange = (value) => {
        this.setState({ downlaodLayers: value })
    }
    render() {
        const { downloadError, downloadLoading, downlaodLayers } = this.state
        const { downloadModalOpen, handleDownloadModal, classes } = this.props
        return (
            <Dialog
                fullScreen
                disableBackdropClick={true}
                open={downloadModalOpen}
                onClose={handleDownloadModal}
                aria-labelledby="form-dialog-title"
            >
                <AppBar className={classes.appBar}>
                    <Toolbar>
                        <IconButton edge="start" color="inherit" onClick={handleDownloadModal} aria-label="Close">
                            <CloseIcon />
                        </IconButton>
                        <Typography className={classNames(classes.flexGrow, classes.whiteText)} noWrap variant="title">
                            {"Download Layers"}
                        </Typography>
                    </Toolbar>
                </AppBar>
                {/* <DialogTitle disableTypography={true} className={classes.dialogTitle}>

                </DialogTitle> */}
                <DialogContent>
                    <DialogContentText>
                        {downloadError && <Typography className={classes.flexGrow} noWrap color="secondary" variant="subheading">{downloadError}</Typography>}
                    </DialogContentText>
                    <Select
                        closeOnSelect={false}
                        multi
                        onChange={this.handleSelectChange}
                        options={downloadableLayers}
                        valueKey={"typename"}
                        labelKey={"title"}
                        placeholder="Layers To Download"
                        removeSelected={this.state.removeSelected}
                        value={downlaodLayers}
                    />
                </DialogContent>
                <DialogActions>
                    {downloadLoading && <CircularProgress className={classes.progress} thickness={7} />}
                    <Button disabled={downloadLoading} onClick={handleDownloadModal} color="primary">
                        {"Cancel"}
                    </Button>
                    <Button onClick={this.downloadSelectedLayers} color="primary">
                        {"Download"}
                    </Button>
                </DialogActions>
            </Dialog>
        )
    }
}
DownloadModal.propTypes = {
    classes: PropTypes.object.isRequired,
    authToken: PropTypes.object.isRequired,
    urls: PropTypes.object.isRequired,
    username: PropTypes.string.isRequired,
    handleDownloadModal: PropTypes.func.isRequired,
    downloadModalOpen: PropTypes.bool.isRequired,
}
const mapStateToProps = (state) => {
    return {
        username: state.username,
        authToken: state.authToken,
        urls: state.urls
    }
}
const mapDispatchToProps = (dispatch) => {
    return {
    }
}
export default connect(mapStateToProps, mapDispatchToProps)(withStyles(styles)(DownloadModal))