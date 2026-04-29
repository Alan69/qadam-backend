from django.contrib import admin

from .models import (
    AvatarItem,
    Challenge,
    ChallengeParticipant,
    Chest,
    Clan,
    ClanBattle,
    ClanMember,
    Friendship,
    League,
    Star,
    Tournament,
    TournamentParticipant,
    UserAvatar,
    UserLeague,
)

for model in (
    League,
    UserLeague,
    Star,
    AvatarItem,
    UserAvatar,
    Chest,
    Tournament,
    TournamentParticipant,
    Clan,
    ClanMember,
    ClanBattle,
    Friendship,
    Challenge,
    ChallengeParticipant,
):
    admin.site.register(model)
