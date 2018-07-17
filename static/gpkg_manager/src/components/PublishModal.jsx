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
import { withStyles } from '@material-ui/core/styles'
const styles = theme => ({
    flexGrow: {
        flexGrow: 1
    },

    progress: {
        margin: theme.spacing.unit * 2,
    },
})
class PublishModal extends React.Component {
    render() {
        const { publishLayer, publishModalOpen, handlPublishModal, publishLoading, classes, publishName, handlePublishName, publishError } = this.props
        return (
            <Dialog
                disableBackdropClick={true}
                open={publishModalOpen}
                onClose={handlPublishModal}
                aria-labelledby="form-dialog-title"
            >
                <DialogTitle id="form-dialog-title">{"Publish Layer"}</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        {publishError && <Typography className={classes.flexGrow} noWrap color="secondary" variant="subheading">{publishError}</Typography>}
                        {`Please Enter Name You Want to publish Layer With.`}
                    </DialogContentText>
                    <TextField
                        inputProps={{ maxLength: 63 }}
                        autoFocus
                        value={publishName}
                        onChange={handlePublishName}
                        margin="dense"
                        id="name"
                        label="Publish Name"
                        fullWidth
                        required
                    />
                </DialogContent>
                <DialogActions>
                    {publishLoading && <CircularProgress className={classes.progress} thickness={7} />}
                    <Button disabled={publishLoading} onClick={handlPublishModal} color="primary">
                        {"Cancel"}
                    </Button>
                    <Button disabled={publishLoading} onClick={publishLayer} color="primary">
                        {"Publish"}
                    </Button>
                </DialogActions>
            </Dialog>
        )
    }
}
PublishModal.propTypes = {
    classes: PropTypes.object.isRequired,
    publishLayer: PropTypes.func.isRequired,
    handlPublishModal: PropTypes.func.isRequired,
    handlePublishName: PropTypes.func.isRequired,
    publishModalOpen: PropTypes.bool.isRequired,
    publishLoading: PropTypes.bool.isRequired,
    publishName: PropTypes.string,
    publishError: PropTypes.string,
}
export default withStyles(styles)(PublishModal)