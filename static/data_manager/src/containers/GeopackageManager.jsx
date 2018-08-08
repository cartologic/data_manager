import 'whatwg-fetch'
import 'babel-polyfill'
import "../css/view.css"

import React, { Component } from 'react'
import { newUploads, uploadsLoading, uploadsTotalCount } from '../actions/uploads'
import { permissions, permissionsLoading } from '../actions/permissions'

import { ApiRequests } from '../utils/utils'
import AppBar from '../components/Appbar'
import Dropzone from 'react-dropzone'
import FileItem from '../components/FileUploadItem'
import FileUploadIcon from '@material-ui/icons/FileUpload'
import GeopackageApi from '../api'
import IconButton from '@material-ui/core/IconButton'
import List from '@material-ui/core/List'
import ListSubheader from '@material-ui/core/ListSubheader'
import { MuiThemeProvider } from '@material-ui/core/styles'
import Paper from '@material-ui/core/Paper'
import PropTypes from 'prop-types'
import { Provider } from 'react-redux'
import Typography from '@material-ui/core/Typography'
import UploadsList from '../components/UploadsList'
import classnames from 'classnames'
import { connect } from 'react-redux'
import { render } from 'react-dom'
import { storeWithInitial } from '../store'
import { theme } from '../themes'
import { withStyles } from '@material-ui/core/styles'

const styles = theme => ({
    fullHeight: {
        height: "100%"
    },
    fullWidth: {
        width: '100%',
    },
    uploadPaper: {
        marginTop: theme.spacing.unit * 2,
        marginBottom: theme.spacing.unit * 2
    },
    button: {
        margin: theme.spacing.unit,
    },
    dropZone: {
        width: "100%",
        padding: '1em',
        flexDirection: 'column',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxSizing: 'border-box',
        textAlign: 'center'
    },
    root: {
        height: `calc( 100% - ${theme.mixins.toolbar['@media (min-width:600px)'].minHeight}px)`,
        [theme.breakpoints.down('sm')]: {
            height: `calc( 100% - ${theme.mixins.toolbar['@media (min-width:0px) and (orientation: landscape)'].minHeight}px)`
        },
        boxSizing: 'border-box',
        ...theme.mixins.gutters(),
        paddingTop: theme.spacing.unit * 2,
        paddingBottom: theme.spacing.unit * 2,
        overflowX: 'scroll',
        zIndex: 0,
        background: '#f3f3f3'

    },
})
class GeopackageManager extends Component {
    constructor(props) {
        super(props)
        const { token, username, urls } = this.props
        this.state = {
            files: [],
        }
        this.geopackageApi = new GeopackageApi(username, token, urls)
        this.requests = new ApiRequests(username, this.token)
    }
    onDrop = (files) => {
        this.setState({
            files
        })
    }
    componentDidMount() {
        const { setUploads, setUploadsLoading, setTotalCount, setPermissions, setPermissionsLoading } = this.props
        this.geopackageApi.getUploads().then(result => {
            setUploads(result.objects)
            setTotalCount(result.meta.total_count)
            setUploadsLoading(false)
        })
        this.geopackageApi.getPermissions().then(result => {
            setPermissions(result)
            setPermissionsLoading(false)
        })
    }
    removeUploadedFile = (file) => {
        const { files } = this.state
        let newFiles = files.filter(tFile => tFile !== file)
        this.setState({ files: newFiles })
    }
    render() {
        const { classes, uploads, uploadsLoading } = this.props
        const { files } = this.state
        return (
            <MuiThemeProvider theme={theme}>
                <div className={classes.fullHeight}>
                    <AppBar title="GeoPackage Manager" />
                    <Paper className={classnames([classes.root])}>
                        <Paper elevation={2}>
                            <Dropzone className={classes.dropZone} accept={".gpkg"} onDrop={this.onDrop}>
                                <label htmlFor="icon-button-file">
                                    <IconButton color="default" className={classes.button} component="span">
                                        <FileUploadIcon />
                                    </IconButton>
                                </label>
                                <Typography variant="display1" gutterBottom>
                                    {"Click to Choose Packages or Drop Packages Here to Upload"}
                                </Typography>
                            </Dropzone>
                        </Paper>
                        {files.length > 0 && <Paper className={classnames([classes.fullWidth], [classes.uploadPaper])} elevation={2}><List
                            className={classes.fullWidth}
                            component="nav"
                            subheader={<ListSubheader component="div">{"Uploading"}</ListSubheader>}
                        >
                            {files.map((file, index) => <FileItem file={file} removeUploadedFile={this.removeUploadedFile} key={index} />)}
                        </List></Paper>}
                        {uploads.length > 0 && !uploadsLoading && <UploadsList />}
                    </Paper>
                </div>
            </MuiThemeProvider>
        )
    }
}
GeopackageManager.propTypes = {
    classes: PropTypes.object.isRequired,
    urls: PropTypes.object.isRequired,
    username: PropTypes.string.isRequired,
    token: PropTypes.string.isRequired,
    setUploads: PropTypes.func.isRequired,
    uploads: PropTypes.array.isRequired,
    uploadsLoading: PropTypes.bool.isRequired,
    setUploadsLoading: PropTypes.func.isRequired,
    setPermissionsLoading: PropTypes.func.isRequired,
    setPermissions: PropTypes.func.isRequired,
    setTotalCount: PropTypes.func.isRequired,
}
const mapStateToProps = (state) => {
    return {
        username: state.username,
        token: state.token,
        urls: state.urls,
        uploads: state.uploads,
        uploadsLoading: state.uploadsLoading,
        permissions: state.permissions,
        permissionsLoading: state.permissionsLoading,
        uploadsTotalCount: state.uploadsTotalCount
    }
}
const mapDispatchToProps = (dispatch) => {
    return {
        setUploadsLoading: (loading) => dispatch(uploadsLoading(loading)),
        setUploads: (uploads) => dispatch(newUploads(uploads)),
        setPermissionsLoading: (loading) => dispatch(permissionsLoading(loading)),
        setPermissions: (perms) => dispatch(permissions(perms)),
        setTotalCount: (count) => dispatch(uploadsTotalCount(count)),
    }
}
let App = connect(mapStateToProps, mapDispatchToProps)(withStyles(styles)(GeopackageManager))
global.GeopackageManagerRenderer = {
    show: (el, props) => {
        render(<Provider store={storeWithInitial(props)}><App /></Provider>, document.getElementById(el))
    }
}