import 'typeface-roboto'

import AppBar from '@material-ui/core/AppBar'
import IconButton from '@material-ui/core/IconButton'
import MenuIcon from '@material-ui/icons/Menu'
import PropTypes from 'prop-types'
import React from 'react'
import Toolbar from '@material-ui/core/Toolbar'
import Typography from '@material-ui/core/Typography'
import { withStyles } from '@material-ui/core/styles'

const styles = {
    root: {
        flexGrow: 1,
    },
    flex: {
        flexGrow: 1,
    }
}

function GeopackageAppBar(props) {
    const { classes, title } = props
    return (
        <div className={classes.root}>
            <AppBar position="static">
                <Toolbar>
                    <Typography variant="title" color="inherit" className={classes.flex}>
                        {title}
                    </Typography>
                </Toolbar>
            </AppBar>
        </div>
    )
}
GeopackageAppBar.propTypes = {
    classes: PropTypes.object.isRequired,
    title: PropTypes.string.isRequired,
}
export default withStyles(styles)(GeopackageAppBar)