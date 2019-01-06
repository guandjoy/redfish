import React from 'react'
import {Link} from 'react-router-dom'
import {connect} from 'react-redux'
import {withRouter} from 'react-router'

import {logout} from '../actions/restAuth'

import Navigation from '../components/Navigation'


class NavigationContainer extends React.Component {
  render() {
    if (this.props.isAuth === true) {
      return (
        <Navigation>
          <ul>
            <Link to="/app"><li>redject</li></Link>
            <Link to="/profile"><li>Profile</li></Link>
            <div onClick={this.props.logout}>
              <li>
                Logout
              </li>
            </div>
          </ul>
          {this.props.children}
        </Navigation>
      )
    } else {
      return (
        <Navigation>
          <ul>
            <Link to="/"><li>redject</li></Link>
            <Link to="/login"><li>Login</li></Link>
            <Link to="/registration"><li>Registration</li></Link>
          </ul>
          {this.props.children}
        </Navigation>
      )
    }
  }
}

const mapStateToProps = state => {
  return {
    isAuth: state.restAuth.isAuth,
    username: state.restAuth.user.username
  }
}

const mapDispatchToProps = dispatch => {
  return {
    logout: () => dispatch(logout()),
  }
}

export default withRouter(connect(mapStateToProps, mapDispatchToProps)(NavigationContainer))
