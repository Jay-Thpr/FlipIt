import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Settings } from 'lucide-react-native';
import { useTheme } from '../contexts/ThemeContext';
import { mockItems, Item } from '../data/mockData';
import ItemCard from '../components/ItemCard';
import AddNewCard from '../components/AddNewCard';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
// Show ~2.3 cards so it's obvious the row is scrollable
const CARD_WIDTH = Math.round(SCREEN_WIDTH * 0.44);

export default function HomeScreen() {
  const { colors } = useTheme();
  const sellItems = mockItems.filter(i => i.type === 'sell');
  const buyItems = mockItems.filter(i => i.type === 'buy');

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <View>
          <Text style={[styles.appName, { color: colors.primary }]}>AgentMarket</Text>
          <Text style={[styles.subtitle, { color: colors.textMuted }]}>
            Autonomous resale agents
          </Text>
        </View>
        <TouchableOpacity
          style={[styles.settingsBtn, { backgroundColor: colors.surface, borderColor: colors.border }]}
          onPress={() => router.push('/settings')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Settings size={18} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scroll}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        <CarouselSection title="Selling" items={sellItems} />
        <CarouselSection title="Buying" items={buyItems} />
      </ScrollView>
    </SafeAreaView>
  );
}

function CarouselSection({ title, items }: { title: string; items: Item[] }) {
  const { colors } = useTheme();
  const activeCount = items.filter(i => i.status === 'active').length;

  return (
    <View style={styles.section}>
      {/* Section header */}
      <View style={styles.sectionHeader}>
        <View style={styles.sectionLeft}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>{title}</Text>
          <View style={[styles.countPill, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={[styles.activeDot, { backgroundColor: colors.accent }]} />
            <Text style={[styles.countText, { color: colors.textSecondary }]}>
              {activeCount} active
            </Text>
          </View>
        </View>
        <Text style={[styles.itemCount, { color: colors.textMuted }]}>
          {items.length} {items.length === 1 ? 'agent' : 'agents'}
        </Text>
      </View>

      {/* Carousel */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.carousel}
        decelerationRate="fast"
        snapToInterval={CARD_WIDTH + 10}
        snapToAlignment="start"
      >
        {items.map(item => (
          <ItemCard
            key={item.id}
            item={item}
            cardWidth={CARD_WIDTH}
            onPress={() => router.push(`/item/${item.id}`)}
          />
        ))}
        <AddNewCard cardWidth={CARD_WIDTH} onPress={() => {}} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 14,
    borderBottomWidth: 1,
  },
  appName: {
    fontSize: 24,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 12,
    marginTop: 1,
  },
  settingsBtn: {
    width: 40,
    height: 40,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },

  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 48 },

  section: {
    paddingTop: 24,
  },

  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    marginBottom: 12,
  },
  sectionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: -0.3,
  },
  countPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    borderRadius: 20,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderWidth: 1,
  },
  activeDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
  },
  countText: {
    fontSize: 11,
    fontWeight: '600',
  },
  itemCount: {
    fontSize: 12,
  },

  carousel: {
    paddingHorizontal: 20,
    gap: 10,
    paddingBottom: 4,
  },
});
