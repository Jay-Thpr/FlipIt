import { View, Text, FlatList, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { mockItems, Message } from '../../data/mockData';
import PlatformBadge from '../../components/PlatformBadge';

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
                  borderWidth: 1,
                  borderColor: colors.border,
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
      <View
        style={[
          styles.header,
          { borderBottomColor: colors.border, backgroundColor: colors.surface },
        ]}
      >
        <TouchableOpacity
          onPress={() => router.back()}
          style={[styles.backBtn, { backgroundColor: colors.muted }]}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={[styles.headerItem, { color: colors.textPrimary }]} numberOfLines={1}>
            {item.name}
          </Text>
          <View style={styles.headerSubRow}>
            <PlatformBadge platform={conversation.platform} />
            <Text style={[styles.headerSub, { color: colors.textMuted }]}>
              @{conversation.username}
            </Text>
          </View>
        </View>
      </View>

      {/* Read-only note */}
      <View style={[styles.logBanner, { backgroundColor: colors.muted, borderBottomColor: colors.border }]}>
        <Text style={[styles.logBannerText, { color: colors.textMuted }]}>
          Log view only — all messages sent by your agent
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
    borderBottomWidth: 1,
  },
  backBtn: {
    width: 38,
    height: 38,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCenter: {
    flex: 1,
    gap: 3,
  },
  headerItem: {
    fontSize: 15,
    fontWeight: '700',
  },
  headerSubRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  headerSub: {
    fontSize: 12,
  },

  logBanner: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderBottomWidth: 1,
  },
  logBannerText: {
    fontSize: 11,
    textAlign: 'center',
    fontWeight: '500',
  },

  messageList: {
    paddingHorizontal: 16,
    paddingVertical: 16,
    gap: 12,
  },

  bubbleWrapper: {
    maxWidth: '80%',
    gap: 3,
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
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },

  bubbleText: {
    fontSize: 14,
    lineHeight: 20,
  },

  timestamp: {
    fontSize: 11,
  },

  emptyText: {
    textAlign: 'center',
    fontSize: 14,
    marginTop: 40,
  },
});
