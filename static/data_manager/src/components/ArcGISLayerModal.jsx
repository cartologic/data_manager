import { ApiRequests } from '../utils/utils'
import Button from '@material-ui/core/Button'
import CircularProgress from '@material-ui/core/CircularProgress'
import Dialog from '@material-ui/core/Dialog'
import DialogActions from '@material-ui/core/DialogActions'
import DialogContent from '@material-ui/core/DialogContent'
import DialogContentText from '@material-ui/core/DialogContentText'
import DialogTitle from '@material-ui/core/DialogTitle'
import PropTypes from 'prop-types'
import React from 'react'
import TextField from '@material-ui/core/TextField'
import Typography from '@material-ui/core/Typography'
import { connect } from 'react-redux'
import validator from 'validator'
import { withStyles } from '@material-ui/core/styles'

const styles = theme => ({
    flexGrow: {
        flexGrow: 1
    },

    progress: {
        margin: theme.spacing.unit * 2,
    },
})
class ArcGISModal extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            sendURLError: null,
            layerURL: '',
            loading: false
        }
        const { token, username } = this.props
        let newToken = token.split(" for ")[0]
        this.requests = new ApiRequests(username, newToken)
    }
    handleLayerURLChange = (event) => {
        this.setState({ layerURL: event.target.value })
    }
    publishArcGISLayer = (event) => {
        const { urls } = this.props
        const { layerURL } = this.state
        const url = `${urls.esriPublishURL}`
        this.requests.doPost(url, JSON.stringify({ layer_url: layerURL }), { 'content-type': 'application/json' }).then(result => {
            if (result.task_id) {
                this.setState({ loading: false, layerURL: '' }, alert("We will send an Email When the Layer is Ready"))
            } else {
                this.setState({ loading: false, sendURLError: result.error_message })
            }
        }).catch(error => {
            this.setState({ loading: false, sendURLError: error.message })
        })
    }
    startPublish = () => {
        const { layerURL } = this.state
        if (layerURL, validator.isURL(layerURL)) {
            this.setState({ loading: true }, this.publishArcGISLayer)
        }
    }
    render() {
        const { layerURL, loading, sendURLError } = this.state
        const { ArcGISModalOpen, handleArcGISModal, classes } = this.props
        return (
            <Dialog
                disableBackdropClick={true}
                open={ArcGISModalOpen}
                onClose={handleArcGISModal}
                aria-labelledby="form-dialog-title"
            >
                <DialogTitle id="form-dialog-title">{"ArcGIS Layer Publisher"}</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        {`Please Enter your Feature Layer URL \n ex:http://x.xx.com/ArcGIS/rest/services/xxx/xx/MapServer/0`}
                    </DialogContentText>
                    {sendURLError && <Typography className={classes.flexGrow} color="secondary" variant="subheading">{sendURLError}</Typography>}
                    <TextField
                        autoFocus
                        value={layerURL}
                        onChange={this.handleLayerURLChange}
                        margin="dense"
                        id="name"
                        label="Layer URL"
                        fullWidth
                        required
                        error={layerURL && !validator.isURL(layerURL) ? true : false}
                    />
                </DialogContent>
                <DialogActions>
                    {loading && <CircularProgress className={classes.progress} thickness={7} />}
                    <Button disabled={loading} onClick={handleArcGISModal} color="primary">
                        {"Cancel"}
                    </Button>
                    <Button disabled={!layerURL || loading || (layerURL && !validator.isURL(layerURL) ? true : false)} onClick={this.startPublish} color="primary">
                        {"Publish"}
                    </Button>
                </DialogActions>
            </Dialog>
        )
    }
}
ArcGISModal.propTypes = {
    classes: PropTypes.object.isRequired,
    handleArcGISModal: PropTypes.func.isRequired,
    ArcGISModalOpen: PropTypes.bool.isRequired,
    token: PropTypes.string.isRequired,
    urls: PropTypes.object.isRequired,
    username: PropTypes.string.isRequired,
}
const mapStateToProps = (state) => {
    return {
        username: state.username,
        token: state.token,
        urls: state.urls
    }
}
const mapDispatchToProps = (dispatch) => {
    return {
    }
}
export default connect(mapStateToProps, mapDispatchToProps)(withStyles(styles)(ArcGISModal))