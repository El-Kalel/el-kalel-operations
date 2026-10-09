# EL-KALEL Mobile App Shell

This is the Capacitor shell for packaging the responsive EL-KALEL web application as Android/iOS apps.

## Android
```bash
npm install
npx cap add android
npx cap sync android
npx cap open android
```

## iOS
```bash
npm install
npx cap add ios
npx cap sync ios
npx cap open ios
```

The production web app URL should be configured through the deployment/build process. Native GPS/camera permissions should be reviewed before store submission.
