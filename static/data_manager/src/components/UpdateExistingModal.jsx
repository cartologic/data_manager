import { ApiRequests } from '../utils/utils'
import Button from '@material-ui/core/Button'
import CircularProgress from '@material-ui/core/CircularProgress'
import Dialog from '@material-ui/core/Dialog'
import DialogActions from '@material-ui/core/DialogActions'
import DialogContent from '@material-ui/core/DialogContent'
import DialogContentText from '@material-ui/core/DialogContentText'
import DialogTitle from '@material-ui/core/DialogTitle'
import FormControl from '@material-ui/core/FormControl'
import IconButton from '@material-ui/core/IconButton'
import Input from '@material-ui/core/Input'
import InputAdornment from '@material-ui/core/InputAdornment'
import InputLabel from '@material-ui/core/InputLabel'
import LayerItem from './LayerItem'
import PropTypes from 'prop-types'
import React from 'react'
import SearchIcon from '@material-ui/icons/Search'
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
class UpdateExistingModal extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            layerTitle: '',
            layers: [],
            layersLoading: false
        }
        const { token, username } = this.props
        let newToken = token.split(" for ")[0]
        this.requests = new ApiRequests(username, newToken)
    }
    handleLayerTitleChange = event => {
        this.setState({ layerTitle: event.target.value })
    }
    handleSearch = () => {

        const { layerTitle } = this.state
        const { urls } = this.props
        const url = `${urls.layersURL}?title__icontains=${layerTitle}&permission=change_resourcebase`
        this.setState({ layersLoading: true }, () => {
            this.requests.doGet(url).then(result => {
                this.setState({ layers: result.objects, layersLoading: false })
            })
        })
    }

    render() {
        const { layers, layersLoading } = this.state
        const { currentLayer, updateExistingModalOpen, handleUpdateExistingModal, updateExistingLoading, classes, updateError } = this.props
        return (
            <Dialog
                fullScreen
                disableBackdropClick={true}
                open={updateExistingModalOpen}
                onClose={handleUpdateExistingModal}
                aria-labelledby="form-dialog-title"
            >
                <DialogTitle disableTypography={true} className={classes.dialogTitle}> <Typography className={classNames(classes.flexGrow, classes.whiteText)} noWrap variant="title">{"Update/Replace Layer"}</Typography></DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        {updateError && <Typography className={classes.flexGrow} noWrap color="secondary" variant="subheading">{updateError}</Typography>}
                        {`Search For The Layer You Want To Replace/Update By ${currentLayer ? currentLayer.name : ''}`}
                    </DialogContentText>
                    <FormControl className={classNames(classes.margin, classes.textField, classes.fullWidth)}>
                        <InputLabel htmlFor="layers-search">{`Layer Name/Layer Title`}</InputLabel>
                        <Input
                            id="layers-search"
                            type={'text'}
                            value={this.state.layerTitle}
                            onChange={this.handleLayerTitleChange}
                            endAdornment={
                                <InputAdornment position="end">
                                    <IconButton
                                        aria-label="Search"
                                        onClick={this.handleSearch}
                                    >
                                        <SearchIcon />
                                    </IconButton>
                                </InputAdornment>
                            }
                            require="true"
                            fullWidth
                        />
                    </FormControl>
                    {!layersLoading && layers.length > 0 && layers.map(layer => {
                        return <LayerItem key={layer.id} currentLayer={currentLayer} layer={layer} />
                    })}
                </DialogContent>
                <DialogActions>
                    {(updateExistingLoading || layersLoading) && <CircularProgress className={classes.progress} thickness={7} />}
                    <Button disabled={updateExistingLoading || layersLoading} onClick={handleUpdateExistingModal} color="primary">
                        {"Cancel"}
                    </Button>
                </DialogActions>
            </Dialog>
        )
    }
}
UpdateExistingModal.propTypes = {
    classes: PropTypes.object.isRequired,
    currentLayer: PropTypes.object,
    token: PropTypes.string.isRequired,
    urls: PropTypes.object.isRequired,
    username: PropTypes.string.isRequired,
    handleUpdateExistingModal: PropTypes.func.isRequired,
    updateExistingModalOpen: PropTypes.bool.isRequired,
    updateExistingLoading: PropTypes.bool.isRequired,
    updateError: PropTypes.string,
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
export default connect(mapStateToProps, mapDispatchToProps)(withStyles(styles)(UpdateExistingModal))