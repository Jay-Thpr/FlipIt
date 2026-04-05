import { StyleSheet, TouchableOpacity } from 'react-native';
import { Plus } from 'lucide-react-native';
import { useTheme } from '../contexts/ThemeContext';

interface Props {
  onPress: () => void;
}

export default function AddNewCard({ onPress }: Props) {
  const { colors } = useTheme();

  return (
    <TouchableOpacity
      style={[styles.btn, { backgroundColor: colors.surface }]}
      onPress={onPress}
      activeOpacity={0.6}
      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
    >
      <Plus size={14} color={colors.textPrimary} strokeWidth={2.5} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  btn: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
