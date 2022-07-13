from django.urls import path

from . import views

app_name = 'bcse'

urlpatterns = [
    path('', views.home, name='home'),
    path('reservation/<int:id>/edit', views.reservationEdit, name='reservationEdit'),
    path('reservation/<int:id>/view', views.reservationView, name='reservationView'),
    path('reservation/<int:id>/delete', views.reservationDelete, name='reservationDelete'),
    path('reservation/<int:id>/message', views.reservationMessage, name='reservationMessage'),
    path('reservation/new', views.reservationEdit, name='reservationNew'),
    path('reservations', views.reservations, name='reservations'),
    path('reservations/search/', views.reservationsSearch, name='reservationsSearch'),
    path('availability/<int:id>', views.getAvailabilityData, name='getAvailabilityData'),
    path('availability/new', views.getAvailabilityData, name='getAvailabilityData'),

    path('workshop/<int:id>/edit', views.workshopEdit, name='workshopEdit'),
    path('workshop/new', views.workshopEdit, name='workshopNew'),
    path('workshop/<int:id>/view', views.workshopView, name='workshopView'),
    path('workshop/<int:id>/copy', views.workshopCopy, name='workshopCopy'),
    path('workshop/<int:id>/delete', views.workshopDelete, name='workshopDelete'),
    path('workshop/<int:id>/registration_setting/edit', views.workshopRegistrationSetting, name='workshopRegistrationSetting'),
    path('workshop/<int:id>/registrants/', views.workshopRegistrants, name='workshopRegistrants'),
    path('workshop/<int:id>/registrants/upload', views.workshopRegistrantsUpload, name='workshopRegistrantsUpload'),

    path('workshop/<int:workshop_id>/registration/', views.workshopRegistration, name='workshopRegistration'),
    path('workshop/<int:workshop_id>/registration/<int:id>/edit', views.workshopRegistrationEdit, name='workshopRegistrationEdit'),
    path('workshop/<int:workshop_id>/registration/<int:id>/delete', views.workshopRegistrationDelete, name='workshopRegistrationDelete'),
    path('workshops/<str:flag>', views.workshops, name='workshops'),
    path('workshops/search/<str:flag>/<str:audience>', views.workshopsSearch, name='workshopsSearch'),
    path('studentPrograms/<str:flag>', views.studentPrograms, name='studentPrograms'),

    path('signin/', views.userSignin, name='signin'),
    path('signin_redirect/', views.signinRedirect, name='signinRedirect'),
    path('signin/<str:user_email>/', views.userSignin, name='signin'),
    path('signup/', views.userSignup, name='signup'),
    path('signout/', views.userSignout, name='signout'),


    path('userProfile/<int:id>/edit', views.userProfileEdit, name='userProfileEdit'),
    path('userProfile/<int:id>/view', views.userProfileView, name='userProfileView'),
    path('userProfile/<int:id>/delete', views.userProfileDelete, name='userProfileDelete'),

    path('adminConfiguration/', views.adminConfiguration, name='adminConfiguration'),

    path('adminConfiguration/activity/<int:id>/edit', views.activityEdit, name='activityEdit'),
    path('adminConfiguration/activity/<int:id>/delete', views.activityDelete, name='activityDelete'),
    path('adminConfiguration/activity/new', views.activityEdit, name='activityNew'),
    path('adminConfiguration/activities/', views.activities, name='activities'),
    path('activity/<int:id>/view', views.activityView, name='activityView'),

    path('adminConfiguration/equipmentType/<int:id>/edit', views.equipmentTypeEdit, name='equipmentTypeEdit'),
    path('adminConfiguration/equipmentType/<int:id>/delete', views.equipmentTypeDelete, name='equipmentTypeDelete'),
    path('adminConfiguration/equipmentType/new', views.equipmentTypeEdit, name='equipmentTypeNew'),
    path('adminConfiguration/equipmentTypes/', views.equipmentTypes, name='equipmentTypes'),
    path('equipmentType/<int:id>/view', views.equipmentTypeView, name='equipmentTypeView'),


    path('adminConfiguration/equipment/<int:id>/edit', views.equipmentEdit, name='equipmentEdit'),
    path('adminConfiguration/equipment/<int:id>/delete', views.equipmentDelete, name='equipmentDelete'),
    path('adminConfiguration/equipment/new', views.equipmentEdit, name='equipmentNew'),
    path('adminConfiguration/equipments/', views.equipments, name='equipments'),
    path('adminConfiguration/baxter_box_usage_report/', views.baxterBoxUsageReport, name='baxterBoxUsageReport'),


    path('adminConfiguration/workshopCategory/<int:id>/edit', views.workshopCategoryEdit, name='workshopCategoryEdit'),
    path('adminConfiguration/workshopCategory/<int:id>/delete', views.workshopCategoryDelete, name='workshopCategoryDelete'),
    path('adminConfiguration/workshopCategory/<int:id>/details', views.getWorkshopCategoryDetails, name='getWorkshopCategoryDetails'),

    path('adminConfiguration/workshopCategory/new', views.workshopCategoryEdit, name='workshopCategoryNew'),
    path('adminConfiguration/workshopCategories/', views.workshopCategories, name='workshopCategories'),
    path('adminConfiguration/workshopsRegistrants/', views.workshopsRegistrants, name='workshopsRegistrants'),
    path('adminConfiguration/registrationEmailMessage/<int:id>/edit', views.registrationEmailMessageEdit, name='registrationEmailMessageEdit'),
    path('adminConfiguration/registrationEmailMessage/<int:id>/delete', views.registrationEmailMessageDelete, name='registrationEmailMessageDelete'),
    path('adminConfiguration/registrationEmailMessage/new', views.registrationEmailMessageEdit, name='registrationEmailMessageNew'),
    path('adminConfiguration/registrationEmailMessages', views.registrationEmailMessages, name='registrationEmailMessages'),

    path('adminConfiguration/teacherLeader/<int:id>/edit', views.teacherLeaderEdit, name='teacherLeaderEdit'),
    path('adminConfiguration/teacherLeader/<int:id>/delete', views.teacherLeaderDelete, name='teacherLeaderDelete'),
    path('adminConfiguration/teacherLeader/new', views.teacherLeaderEdit, name='teacherLeaderNew'),
    path('adminConfiguration/teacherLeaders/', views.teacherLeaders, name='teacherLeaders'),

    path('adminConfiguration/users/', views.users, name='users'),
    path('adminConfiguration/users/search', views.usersSearch, name='usersSearch'),
    path('adminConfiguration/users/upload', views.usersUpload, name='usersUpload'),

    path('adminConfiguration/workPlace/<int:id>/edit', views.workPlaceEdit, name='workPlaceEdit'),
    path('adminConfiguration/workPlace/<int:id>/delete', views.workPlaceDelete, name='workPlaceDelete'),
    path('adminConfiguration/workPlace/new', views.workPlaceEdit, name='workPlaceNew'),
    path('adminConfiguration/workPlaces/search', views.workPlacesSearch, name='workPlacesSearch'),
    path('adminConfiguration/workPlaces/', views.workPlaces, name='workPlaces'),

    path('adminConfiguration/teamMembers/', views.teamMembers, name='teamMembers'),
    path('adminConfiguration/teamMember/<int:id>/edit', views.teamMemberEdit, name='teamMemberEdit'),
    path('adminConfiguration/teamMember/<int:id>/delete', views.teamMemberDelete, name='teamMemberDelete'),
    path('adminConfiguration/teamMember/new', views.teamMemberEdit, name='teamMemberNew'),


    path('adminConfiguration/partners/', views.partners, name='partners'),
    path('adminConfiguration/partner/<int:id>/edit', views.partnerEdit, name='partnerEdit'),
    path('adminConfiguration/partner/<int:id>/delete', views.partnerDelete, name='partnerDelete'),
    path('adminConfiguration/partner/new', views.partnerEdit, name='partnerNew'),

    path('adminConfiguration/surveys/', views.surveys, name='surveys'),
    path('adminConfiguration/survey/<int:id>/edit', views.surveyEdit, name='surveyEdit'),
    path('adminConfiguration/survey/<int:id>/delete', views.surveyDelete, name='surveyDelete'),
    path('adminConfiguration/survey/new', views.surveyEdit, name='surveyNew'),
    path('adminConfiguration/survey/<int:id>/submissions', views.surveySubmissions, name='surveySubmissions'),
    path('adminConfiguration/survey/<int:id>/page/<int:page_num>', views.surveyPreview, name='surveyPreview'),

    path('adminConfiguration/survey/<int:id>/submission/<uuid:submission_uuid>/view', views.surveySubmissionView, name='surveySubmissionView'),
    path('adminConfiguration/survey/<int:id>/submission/<uuid:submission_uuid>/edit', views.surveySubmissionEdit, name='surveySubmissionEdit'),
    path('adminConfiguration/survey/<int:id>/submission/<uuid:submission_uuid>/delete', views.surveySubmissionDelete, name='surveySubmissionDelete'),

    path('adminConfiguration/survey/<int:survey_id>/surveyComponent/<int:id>/edit', views.surveyComponentEdit, name='surveyComponentEdit'),
    path('adminConfiguration/survey/<int:survey_id>/surveyComponent/<int:id>/delete', views.surveyComponentDelete, name='surveyComponentDelete'),
    path('adminConfiguration/survey/<int:survey_id>/surveyComponent/new', views.surveyComponentEdit, name='surveyComponentNew'),

    path('survey/<int:survey_id>/submission/<uuid:submission_uuid>/page/<int:page_num>', views.surveySubmission, name='surveySubmission'),

    path('survey/<int:survey_id>/submission/new', views.surveySubmission, name='surveySubmissionNew'),



    path('baxter_box/info/', views.baxterBoxInfo, name='baxterBoxInfo'),

    path('baxter_box/support/', views.classroomSupport, name='classroomSupport'),
    path('about/bcse', views.aboutBCSE, name='aboutBCSE'),
    path('about/centers', views.aboutCenters, name='aboutCenters'),
    path('about/partners', views.aboutPartners, name='aboutPartners'),
    path('about/team', views.aboutTeam, name='aboutTeam'),
    path('about/case_study', views.aboutCaseStudy, name='aboutCaseStudy'),
    path('about/contact', views.contactUs, name='contactUs')

]
