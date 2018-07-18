import { ApiRequests } from '../utils/utils'
import Button from '@material-ui/core/Button'
import CircularProgress from '@material-ui/core/CircularProgress'
import Collapse from '@material-ui/core/Collapse'
import List from '@material-ui/core/List'
import ListItem from '@material-ui/core/ListItem'
import ListItemText from '@material-ui/core/ListItemText'
import ListSubheader from '@material-ui/core/ListSubheader'
import Paper from '@material-ui/core/Paper'
import PropTypes from 'prop-types'
import React from 'react'
import Tooltip from '@material-ui/core/Tooltip'
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
    progress: {
        margin: theme.spacing.unit * 2,
    },
    layerItem: {
        margin: theme.spacing.unit * 2,
        display: 'flex',
        flexDirection: 'column'
    }, layerItemActions: {
        display: 'flex',
        [theme.breakpoints.down('sm')]: {
            flexDirection: 'column'
        },

        alignItems: 'center',
        justifyContent: 'space-between'
    },
    content: {
        padding: theme.spacing.unit
    },
    schemaFields: {
        display: 'flex',
        justifyContent: 'space-around'
    }, textCenter: {
        textAlign: 'center'
    }
})
class LayerItem extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            schema: null,
            schemaLoading: null,
            reloadLayerLoading: false,
            replaceLayerLoading: false,
            expand: false
        }
        const { token, username } = this.props
        let newToken = token.split(" for ")[0]
        this.requests = new ApiRequests(username, newToken)
    }
    loadSchema = () => {
        const { urls, layer, currentLayer } = this.props
        const url = urls.compareLayerURL(currentLayer.upload_id, currentLayer.name, layer.alternate)
        this.requests.doGet(url).then(result => {
            if (result.error_message) {
                this.setState({ schemaLoading: false, schema: null }, alert(result.error_message))
            } else {
                this.setState({ schema: result, schemaLoading: false, expand: true })
            }
        }).catch(function (err) {
            this.setState({ schemaLoading: false, schema: null }, alert(err.message))
        }.bind(this))
    }
    compareSchema = () => {
        const { schema, expand } = this.state
        if (!schema) {
            this.setState({ schemaLoading: true, expand: false }, this.loadSchema)

        } else {
            this.setState({ expand: !expand })
        }
    }
    reloadLayer = () => {
        const { urls, layer, currentLayer } = this.props
        const url = urls.reloadURL(currentLayer.upload_id, currentLayer.name, layer.alternate)
        this.requests.doGet(url).then(result => {
            if (result.error_message) {
                this.setState({ reloadLayerLoading: false }, alert(result.error_message))
            } else {
                this.setState({ reloadLayerLoading: false }, () => alert(result.status))
            }
        }).catch(function (err) {
            this.setState({ reloadLayerLoading: false }, alert(err.message))
        }.bind(this))
    }
    startReloadLayer = () => {
        this.setState({ reloadLayerLoading: true }, this.reloadLayer)
    }
    replaceLayer = () => {
        const { layer, currentLayer } = this.props
        const url = `${currentLayer.urls.publish_url}?replace=true&publish_name=${layer.alternate.split(":").pop()}`
        this.requests.doGet(url).then(result => {
            if (result.error_message) {
                this.setState({ replaceLayerLoading: false }, alert(result.error_message))
            } else {
                this.setState({ replaceLayerLoading: false }, () => window.location.href = result.layer_url)
            }
        }).catch(function (err) {
            this.setState({ replaceLayerLoading: false }, alert(err.message))
        }.bind(this))
    }
    startReplaceLayer = () => {
        this.setState({ replaceLayerLoading: true }, this.replaceLayer)
    }
    render() {
        const { layer, classes } = this.props
        const { schema, schemaLoading, expand, reloadLayerLoading, replaceLayerLoading } = this.state
        return (
            <Paper key={layer.id} className={classes.layerItem} elevation={2}>
                <div className={classes.layerItemActions}>
                    <Typography noWrap className={classNames(classes.flexGrow, classes.button)} variant="subheading">{layer.title}</Typography>
                    {schemaLoading && <CircularProgress className={classes.progress} thickness={5} />}
                    {reloadLayerLoading && <CircularProgress color="default" className={classes.progress} thickness={5} />}
                    {replaceLayerLoading && <CircularProgress color="secondary" className={classes.progress} thickness={5} />}
                    <Tooltip title="Comapare The Schema of this Layer With the Target Layer and return the result">
                        <Button onClick={this.compareSchema} variant="outlined" color="primary" className={classes.button}>
                            {"Compare Schema"}
                        </Button>
                    </Tooltip>
                    <Tooltip title="Completly Replace Layer i.e(replace Layer Portal Record, Styles, Database Table, Geoserver Layer and thumbnails)">
                        <Button onClick={this.startReplaceLayer} variant="outlined" color="secondary" className={classes.button}>
                            {"Replace"}
                        </Button>
                    </Tooltip>
                    <Tooltip title="Replace Current Database Table With This One">
                        <Button onClick={this.startReloadLayer} variant="outlined" color="default" className={classes.button}>
                            {"Update(DB Table Replacement)"}
                        </Button>
                    </Tooltip>
                </div>
                <Collapse in={expand} timeout="auto" unmountOnExit>
                    <div className={classes.content}>
                        <div className={classes.textCenter}>
                            {!schemaLoading && schema && < Typography color={schema.compatible ? "primary" : "secondary"} noWrap className={classNames(classes.flexGrow, classes.button)} variant="title">{`Layer is ${schema.compatible ? "Compatible" : "Incompatible"}`}</Typography>}
                        </div>
                        <div className={classes.schemaFields}>
                            {!schemaLoading && schema && schema.new_fields.length > 0 && <List
                                component="nav"
                                subheader={<ListSubheader component="div">{"New Fields"}</ListSubheader>}
                            >
                                {schema.new_fields.map((field, index) => {
                                    return <ListItem key={index}>
                                        <ListItemText inset primary={`Field: ${field[0]}`} secondary={`Type: ${field[1]}`} />
                                    </ListItem>
                                })}
                            </List>}
                            {!schemaLoading && schema && schema.deleted_fields.length > 0 && <List
                                component="nav"
                                subheader={<ListSubheader component="div">{"Deleted Fields"}</ListSubheader>}
                            >
                                {schema.deleted_fields.map((field, index) => {
                                    return <ListItem key={index}>
                                        <ListItemText inset primary={`Field: ${field[0]}`} secondary={`Type: ${field[1]}`} />
                                    </ListItem>
                                })}
                            </List>}
                        </div>
                    </div>
                </Collapse>
            </Paper >
        )
    }
}
LayerItem.propTypes = {
    classes: PropTypes.object.isRequired,
    token: PropTypes.string.isRequired,
    urls: PropTypes.object.isRequired,
    username: PropTypes.string.isRequired,
    layer: PropTypes.object.isRequired,
    currentLayer: PropTypes.object.isRequired
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
export default connect(mapStateToProps, mapDispatchToProps)(withStyles(styles)(LayerItem))