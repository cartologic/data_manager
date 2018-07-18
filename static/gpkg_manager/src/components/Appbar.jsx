import 'typeface-roboto'

import AppBar from '@material-ui/core/AppBar'
import Button from '@material-ui/core/Button'
import DownloadModal from './DownloadModal'
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

class GeopackageAppBar extends React.Component {
    state = {
        downloadModalOpen: false
    }
    handleDownloadModal = () => {
        const { downloadModalOpen } = this.state
        this.setState({ downloadModalOpen: !downloadModalOpen })
    }
    render() {
        const { downloadModalOpen } = this.state
        const { classes, title } = this.props
        return (
            <div className={classes.root}>
                <AppBar position="static">
                    <Toolbar>
                        <Typography variant="title" color="inherit" className={classes.flex}>
                            {title}
                        </Typography>
                        <Button onClick={this.handleDownloadModal} color="inherit">{"Download"}</Button>
                    </Toolbar>
                </AppBar>
                <DownloadModal handleDownloadModal={this.handleDownloadModal} downloadModalOpen={downloadModalOpen} />
            </div>
        )
    }
}
GeopackageAppBar.propTypes = {
    classes: PropTypes.object.isRequired,
    title: PropTypes.string.isRequired,
}
export default withStyles(styles)(GeopackageAppBar)