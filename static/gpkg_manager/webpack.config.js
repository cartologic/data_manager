var webpack = require( 'webpack' )
var ExtractTextPlugin = require( "extract-text-webpack-plugin" )
var path = require( 'path' )
var BUILD_DIR = path.resolve( __dirname, 'dist' )
var APP_DIR = path.resolve( __dirname, 'src' )
var filename = '[name].bundle.js'
const plugins = [
    new ExtractTextPlugin( {
        allChunks: true,
        filename: "[name].css",
    } ),
    new webpack.SourceMapDevToolPlugin( {
        filename: 'sourcemaps/[file].map',
        publicPath: '/static/gpkg_manager/dist/',
        fileContext: 'public'
    } ),

]
var config = {
    entry: {
        GeopackageManager: path.join( APP_DIR, 'containers',
            'GeopackageManager.jsx' ),
    },
    optimization: {
        splitChunks: {
            chunks: "all",
            automaticNameDelimiter: '-'
        }
    },
    devtool: 'eval-cheap-module-source-map',
    output: {
        path: BUILD_DIR,
        filename: filename,
        library: '[name]',
        libraryTarget: 'umd',
        umdNamedDefine: true,
        chunkFilename: '[name]-chunk.js',
        publicPath: "/static/gpkg_manager/dist/"
    },
    node: {
        fs: "empty"
    },
    plugins: plugins,
    resolve: {
        extensions: [ '*', '.js', '.jsx' ],
        alias: {
            Source: APP_DIR
        },
    },
    module: {
        rules: [ {
            test: /\.(js|jsx)$/,
            exclude: /(node_modules|bower_components)/,
            use: {
                loader: 'babel-loader',
                options: {
                    cacheDirectory: true,
                    presets: [ "es2015",
                        "stage-1",
                        "react" ],
                    plugins: [ "transform-object-rest-spread",
                        'transform-runtime' ]
                }
            }
        }, {
            test: /\.css$/,
            loader: ExtractTextPlugin.extract( {
                use: {
                    loader: 'css-loader',
                    options: {
                        minimize: true
                    }
                },
                fallback: 'style-loader'
            } )
        },
        {
            test: /\.xml$/,
            loader: 'raw-loader'
        },
        {
            type: 'javascript/auto',
            test: /\.json$/,
            loader: "json-loader"
        },
        {
            test: /\.(png|jpg|gif)$/,
            loader: 'file-loader'
        },
        {
            test: /\.(woff|woff2)$/,
            loader: 'url-loader?limit=100000'
        }
        ],
        noParse: [ /dist\/ol\.js/, /dist\/jspdf.debug\.js/,
            /dist\/js\/tether\.js/ ]
    }
}
module.exports = config
