import { View, Text, FlatList, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { mockItems, Message, PLATFORM_NAMES } from '../../data/mockData';

export default function ChatLogScreen() {
  const { id, itemId } = useLocalSearchParams<{ id: string; itemId: string }>();
  const { colors } = useTheme();

  const item = mockItems.find(i => i.id === itemId);
  const conversation = item?.conversations.find(c => c.id === id);

  if (!item || !conversation) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={{ padding: 24, color: colors.textMuted }}>Conversation not found.</Text>
      </SafeAreaView>
    );
  }

  const renderMessage = ({ item: msg }: { item: Message }) => {
    const isAgent = msg.sender === 'agent';
    return (
      <View style={[styles.bubbleWrapper, isAgent ? styles.wrapperRight : styles.wrapperLeft]}>
        <View
          style={[
            styles.bubble,
            isAgent
              ? { backgroundColor: colors.primary, borderBottomRightRadius: 4 }
              : {
                  backgroundColor: colors.surface,
                  borderBottomLeftRadius: 4,
                },
          ]}
        >
          <Text
            style={[
              styles.bubbleText,
              { color: isAgent ? colors.onPrimary : colors.textPrimary },
            ]}
          >
            {msg.text}
          </Text>
        </View>
        <Text style={[styles.timestamp, { color: colors.textMuted }]}>{msg.timestamp}</Text>
      </View>
    );
  };

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={['top', 'bottom']}
    >
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={[styles.headerContact, { color: colors.textPrimary }]} numberOfLines={1}>
            @{conversation.username}
          </Text>
          <Text style={[styles.headerItem, { color: colors.textMuted }]} numberOfLines={1}>
            {item.name}
          </Text>
        </View>
        <Text style={[styles.platformName, { color: colors.textSecondary }]}>
          {PLATFORM_NAMES[conversation.platform]}
        </Text>
      </View>

      {/* Messages */}
      <FlatList
        data={conversation.messages}
        keyExtractor={m => m.id}
        contentContainerStyle={styles.messageList}
        renderItem={renderMessage}
        ListEmptyComponent={
          <Text style={[styles.emptyText, { color: colors.textMuted }]}>No messages yet.</Text>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 10,
  },
  backBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCenter: {
    flex: 1,
    gap: 2,
  },
  headerContact: {
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: -0.2,
  },
  headerItem: {
    fontSize: 12,
  },
  platformName: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },

  messageList: {
    paddingHorizontal: 16,
    paddingVertical: 16,
    gap: 12,
  },

  bubbleWrapper: {
    maxWidth: '78%',
    gap: 4,
  },
  wrapperRight: {
    alignSelf: 'flex-end',
    alignItems: 'flex-end',
  },
  wrapperLeft: {
    alignSelf: 'flex-start',
    alignItems: 'flex-start',
  },

  bubble: {
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },

  bubbleText: {
    fontSize: 14,
    lineHeight: 20,
  },

  timestamp: {
    fontSize: 11,
    fontVariant: ['tabular-nums'],
  },

  emptyText: {
    textAlign: 'center',
    fontSize: 14,
    marginTop: 40,
  },
});
