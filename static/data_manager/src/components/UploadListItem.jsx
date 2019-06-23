import { ApiRequests, checkPermission } from '../utils/utils'

import Button from '@material-ui/core/Button'
import ExpandMoreIcon from '@material-ui/icons/ExpandMore'
import ExpansionPanel from '@material-ui/core/ExpansionPanel'
import ExpansionPanelActions from '@material-ui/core/ExpansionPanelActions'
import ExpansionPanelDetails from '@material-ui/core/ExpansionPanelDetails'
import ExpansionPanelSummary from '@material-ui/core/ExpansionPanelSummary'
import PropTypes from 'prop-types'
import React from 'react'
import Table from '@material-ui/core/Table'
import TableBody from '@material-ui/core/TableBody'
import TableCell from '@material-ui/core/TableCell'
import TableHead from '@material-ui/core/TableHead'
import TableRow from '@material-ui/core/TableRow'
import Typography from '@material-ui/core/Typography'
import { connect } from 'react-redux'
import { deleteUpload } from '../actions/uploads'
import { withStyles } from '@material-ui/core/styles'

const styles = theme => ({
    root: {
        width: '100%',
        marginTop: theme.spacing.unit * 2,
        marginBottom: theme.spacing.unit * 2,
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
        [theme.breakpoints.down('sm')]: {
            flexDirection: 'column',
            padding: theme.spacing.unit
        },
        overflow: 'hidden',
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
const CustomTableCell = withStyles(theme => ({
    head: {
        backgroundColor: theme.palette.primary.dark,
        color: theme.palette.common.white,
    },
    body: {
        fontSize: 14,
    },
}))(TableCell)
class UploadListItem extends React.Component {
    constructor(props) {
        super(props)
        const { authToken, username } = this.props
        this.requests = new ApiRequests(username, authToken)
    }
    handleDeleted = (upload) => {
        const { urls, deleteOldUpload } = this.props
        const targetURL = `${urls.uploadsURL}${upload.id}/`
        this.requests.doDelete(targetURL).then(result => {
            deleteOldUpload(upload.id)
        })
    }
    render() {
        const { classes, upload, permissions, setCurrentLayerOpenPublishModal, setCurrentLayerOpenUpdateModal, permissionsLoading } = this.props
        return (
            <ExpansionPanel defaultExpanded>
                <ExpansionPanelSummary classes={{ content: classes.panelSummary }} expandIcon={<ExpandMoreIcon />}>
                    <Typography className={classes.flexGrow} noWrap variant="subheading">{upload.package.split("/").pop()}</Typography>
                    <Typography className={classes.flexGrow} noWrap variant="subheading">{`Uploaded At: ${new Date(upload.uploaded_at).toLocaleString()}`}</Typography>
                    <div>
                        <Typography className={classes.flexGrow} noWrap variant="subheading">{`Owner: ${upload.user.username}`}</Typography>
                    </div>
                </ExpansionPanelSummary>
                <ExpansionPanelDetails>
                    <div className={classes.tableWrapper}>
                        <Table className={classes.table}>
                            <TableHead>
                                <TableRow>
                                    <CustomTableCell className={classes.textCenter}>{"Layer Name"}</CustomTableCell>
                                    <CustomTableCell className={classes.textCenter}>{"Layer Type"}</CustomTableCell>
                                    <CustomTableCell className={classes.textCenter}>{"Feature Count"}</CustomTableCell>
                                    <CustomTableCell className={classes.textCenter}>{"Actions"}</CustomTableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {!permissionsLoading && upload.layers.map((layer, index) => {
                                    return (
                                        <TableRow className={classes.row} key={index}>
                                            <TableCell className={classes.textCenter} component="th" scope="row">
                                                <Typography noWrap variat="body2">{layer.name}</Typography>
                                            </TableCell>
                                            <TableCell className={classes.textCenter} component="th" scope="row">
                                                <Typography noWrap variat="body2">{layer.geometry_type_name}</Typography>
                                            </TableCell >
                                            <TableCell className={classes.textCenter} component="th" scope="row">
                                                <Typography noWrap variat="body2">{layer.feature_count}</Typography>
                                            </TableCell>
                                            <TableCell className={classes.textCenter} component="th" scope="row">
                                                {checkPermission(permissions, 'publish_from_package', upload.id) && <Button onClick={() => setCurrentLayerOpenPublishModal(layer)} variant="contained" color="primary" className={classes.button}>
                                                    {"Publish New"}
                                                </Button>}
                                                {checkPermission(permissions, 'publish_from_package', upload.id) && <Button variant="contained" onClick={() => setCurrentLayerOpenUpdateModal({ ...layer, upload_id: upload.id })} color="secondary" className={classes.button}>
                                                    {"Update Existing"}
                                                </Button>}
                                            </TableCell>
                                        </TableRow>
                                    )
                                })}
                            </TableBody>
                        </Table>
                    </div>
                </ExpansionPanelDetails>
                <ExpansionPanelActions>
                    {!permissionsLoading && checkPermission(permissions, 'download_package', upload.id) && <Button component="a" href={upload.download_url} size="small" variant="outlined" color="primary" className={classes.button}>
                        {"Download"}
                    </Button>}
                    {!permissionsLoading && checkPermission(permissions, 'delete_package', upload.id) && <Button onClick={() => this.handleDeleted(upload)} size="small" variant="outlined" color="secondary" className={classes.button}>
                        {"Delete"}
                    </Button>}
                </ExpansionPanelActions>
            </ExpansionPanel>
        )
    }
}
UploadListItem.propTypes = {
    classes: PropTypes.object.isRequired,
    deleteOldUpload: PropTypes.func.isRequired,
    setCurrentLayerOpenPublishModal: PropTypes.func.isRequired,
    setCurrentLayerOpenUpdateModal: PropTypes.func.isRequired,
    upload: PropTypes.object.isRequired,
    permissions: PropTypes.object.isRequired,
    authToken: PropTypes.object.isRequired,
    urls: PropTypes.object.isRequired,
    username: PropTypes.string.isRequired,
    permissionsLoading: PropTypes.bool.isRequired,
}
const mapStateToProps = (state) => {
    return {
        username: state.username,
        authToken: state.authToken,
        urls: state.urls,
        permissions: state.permissions,
        permissionsLoading: state.permissionsLoading
    }
}
const mapDispatchToProps = (dispatch) => {
    return {
        deleteOldUpload: (uploadID) => dispatch(deleteUpload(uploadID)),
    }
}
export default connect(mapStateToProps, mapDispatchToProps)(withStyles(styles)(UploadListItem))