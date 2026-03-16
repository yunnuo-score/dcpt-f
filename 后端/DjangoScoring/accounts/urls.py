from django.urls import path
from .views import RegisterView, LoginView, SendCodeView, ResetPasswordView,UserListView, UpdateUserRoleView,InviteCodeListView, GenerateInviteCodeView, AdminCreateUserView
from .views import DeleteUserView,UserProfileView, UpdateUserProfileView,SecuritySettingsView,DeleteAccountView,CheckUsernameView
urlpatterns = [
    path('api/auth/register', RegisterView.as_view(), name='register'),
    path('api/auth/login', LoginView.as_view(), name='login'),
    path('api/auth/send-code', SendCodeView.as_view(), name='send_code'),
    path('api/auth/reset-password', ResetPasswordView.as_view(), name='reset-password'),
    path('api/users/list', UserListView.as_view(), name='user_list'),
    path('api/users/update-role', UpdateUserRoleView.as_view(), name='update_user_role'),
    path('api/invite-codes/list', InviteCodeListView.as_view(), name='invite_code_list'),
    path('api/invite-codes/generate', GenerateInviteCodeView.as_view(), name='invite_code_generate'),
    path('api/users/admin-create', AdminCreateUserView.as_view(), name='admin_create_user'),
    path('api/users/delete', DeleteUserView.as_view(), name='delete_user'),
    path('api/users/profile', UserProfileView.as_view(), name='user_profile'),
    path('api/users/profile/update', UpdateUserProfileView.as_view(), name='update_user_profile'),
    path('api/users/security-update', SecuritySettingsView.as_view(), name='security_update'),
    path('api/users/profile/delete', DeleteAccountView.as_view(), name='delete_profile'),
    path('api/auth/check-username', CheckUsernameView.as_view()),
]