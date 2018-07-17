import blue from '@material-ui/core/colors/blue'
import { createMuiTheme } from '@material-ui/core/styles'
import deepOrange from '@material-ui/core/colors/deepOrange'
import red from '@material-ui/core/colors/red'
export const theme = createMuiTheme({
    palette: {
        primary: blue,
        secondary: red,
        error: deepOrange,
    },
})