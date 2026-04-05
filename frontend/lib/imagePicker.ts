import { Alert, ActionSheetIOS, Platform } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

interface PickImageOptions {
  /** 'circle' for profile pics (1:1), 'rectangle' for item photos (4:3) */
  shape?: 'circle' | 'rectangle';
  /** Allow selecting multiple images (only applies to library, not camera) */
  multiple?: boolean;
  /** Image quality 0-1 */
  quality?: number;
}

async function requestCameraPermission(): Promise<boolean> {
  const { status } = await ImagePicker.requestCameraPermissionsAsync();
  if (status !== 'granted') {
    Alert.alert('Camera Permission', 'Please allow camera access in your device settings to take photos.');
    return false;
  }
  return true;
}

async function pickFromLibrary(options: PickImageOptions): Promise<string[]> {
  const aspect: [number, number] = options.shape === 'circle' ? [1, 1] : [4, 3];

  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    allowsEditing: !options.multiple,  // editing only works with single selection
    allowsMultipleSelection: options.multiple ?? false,
    aspect,
    quality: options.quality ?? 0.8,
  });

  if (result.canceled) return [];
  return result.assets.map(a => a.uri);
}

async function takePhoto(options: PickImageOptions): Promise<string[]> {
  const hasPermission = await requestCameraPermission();
  if (!hasPermission) return [];

  const aspect: [number, number] = options.shape === 'circle' ? [1, 1] : [4, 3];

  const result = await ImagePicker.launchCameraAsync({
    allowsEditing: true,  // always allow cropping after taking photo
    aspect,
    quality: options.quality ?? 0.8,
  });

  if (result.canceled) return [];
  return result.assets.map(a => a.uri);
}

/**
 * Shows an action sheet to pick from library or take a photo,
 * then returns the selected image URI(s) with cropping applied.
 */
export function pickImage(options: PickImageOptions = {}): Promise<string[]> {
  return new Promise((resolve) => {
    const actions = [
      { label: 'Take Photo', action: () => takePhoto(options).then(resolve) },
      { label: 'Choose from Library', action: () => pickFromLibrary(options).then(resolve) },
    ];

    if (Platform.OS === 'ios') {
      ActionSheetIOS.showActionSheetWithOptions(
        {
          options: ['Cancel', ...actions.map(a => a.label)],
          cancelButtonIndex: 0,
        },
        (buttonIndex) => {
          if (buttonIndex === 0) {
            resolve([]);
          } else {
            actions[buttonIndex - 1].action();
          }
        }
      );
    } else {
      // Android: use Alert as action sheet
      Alert.alert(
        'Add Photo',
        undefined,
        [
          { text: 'Cancel', style: 'cancel', onPress: () => resolve([]) },
          ...actions.map(a => ({ text: a.label, onPress: a.action })),
        ]
      );
    }
  });
}
